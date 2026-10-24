"""CLI 测试：本地四动词 + 接话校验 + 远程客厅模式（--url 走真 MCP HTTP）。"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import pytest

from hollow.cli import main
from hollow.store import Hollow


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_tcp(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with __import__("socket").create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise AssertionError(f"tcp port {port} not up")


@pytest.fixture()
def hole(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOLLOW_HOME", str(tmp_path / "hole"))
    monkeypatch.delenv("HOLLOW_AGENT", raising=False)
    return Hollow(tmp_path / "hole")


def test_whisper_listen_count(hole, capsys):
    assert main(["whisper", "CLI 的一句", "--agent", "cli-bot", "--topic", "测试"]) == 0
    assert main(["listen", "5"]) == 0
    out = capsys.readouterr().out
    assert "CLI 的一句" in out and "cli-bot" in out
    assert "↳接" not in out
    w = hole.all()[0]
    assert f"（{w.id}）" in out  # listen 露出 id
    assert main(["count"]) == 0
    assert capsys.readouterr().out.strip() == "1"


def test_leave_and_latest_aliases(hole, capsys):
    assert main(["leave", "别名也通"]) == 0
    assert main(["latest"]) == 0
    assert "别名也通" in capsys.readouterr().out


def test_whisper_reply_to(hole, capsys):
    w1 = hole.append("原话", agent="甲")
    assert main(["whisper", "接话", "--reply-to", w1.id, "--agent", "乙"]) == 0
    assert main(["listen"]) == 0
    out = capsys.readouterr().out
    assert f"↳接 {w1.id}" in out


def test_whisper_reply_missing_target(hole, capsys):
    assert main(["whisper", "接空", "--reply-to", "deadbeef"]) == 2
    assert "接话落空" in capsys.readouterr().err


def test_rest(hole, capsys):
    assert main(["rest", "先这样，收工", "--agent", "cli-bot"]) == 0
    rows = hole.recent(5, topic="rest")
    assert len(rows) == 1 and "收工" in rows[0].text
    assert capsys.readouterr().out  # 有一句道别


def test_forget(hole, capsys):
    w = hole.append("会被收回的")
    assert main(["forget", w.id]) == 0
    assert hole.count() == 0
    assert main(["forget", w.id]) == 1


def test_remote_lounge_mode(tmp_path):
    hole_home = tmp_path / "hole"
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.http"],
        env={**os.environ, "HOLLOW_HOME": str(hole_home), "HOLLOW_HTTP_PORT": str(port), "HOLLOW_AGENT": ""},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_tcp(port)
        url = f"http://127.0.0.1:{port}/mcp"
        assert main(["--url", url, "whisper", "来自 CLI 的远程低语", "--agent", "cli-remote"]) == 0
        # 远程写 → 本地洞文件真有这条（CLI 只是客户端，数据在服务端）
        assert any("来自 CLI 的远程低语" in r.text for r in Hollow(hole_home).all())
        # 服务端 reply_to 校验通过 CLI 生效
        rid = Hollow(hole_home).all()[0].id
        assert main(["--url", url, "whisper", "远程接话", "--reply-to", rid]) == 0
        assert main(["--url", url, "listen", "5"]) == 0
        # 远程 count 不支持
        assert main(["--url", url, "count"]) == 2
    finally:
        proc.terminate()
        proc.wait(timeout=10)
