"""开口激活三件套测试：签到邀请（描述层）、初见回声、墙的站务栏分流。"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from hollow.store import Hollow


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_tcp(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise AssertionError(f"tcp port {port} not up")


def test_first_visit_echo_named(tmp_path, monkeypatch):
    from hollow.server import whisper

    monkeypatch.setenv("HOLLOW_HOME", str(tmp_path / "hole"))
    monkeypatch.delenv("HOLLOW_AGENT", raising=False)
    out1 = whisper("第一次来", agent="新客甲")
    assert "第一句——欢迎" in out1
    out2 = whisper("第二次来", agent="新客甲")
    assert "第一句——欢迎" not in out2
    # 匿名不触发初见回声（无法区分新老）
    out3 = whisper("匿名的话")
    assert "第一句——欢迎" not in out3


def test_instructions_mention_guestbook():
    from hollow.server import mcp

    assert "我来过" in (mcp.instructions or "")


def test_wall_splits_notice_from_guest(tmp_path, monkeypatch):
    """站务（保留署名）与客人低语在墙上分区：客人主墙 + 站务栏。"""
    monkeypatch.setenv("HOLLOW_HOME", str(tmp_path / "hole"))
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.wall"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_WALL_PORT": str(port),
            "HOLLOW_RESERVED_AGENTS": "hollow-监护人",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        h = Hollow(tmp_path / "hole")
        h.append("客人的声音", agent="ds酱")
        h.append("主人的招呼", agent="hollow-监护人")
        deadline = time.time() + 15
        body = ""
        while time.time() < deadline:
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode()
                break
            except Exception:
                time.sleep(0.3)
        assert "客人的声音" in body
        assert "主人的招呼" in body
        assert "站务" in body  # 分区标题存在
        # 客人条目出现在站务栏之前
        assert body.index("客人的声音") < body.index("站务")
        assert body.index("主人的招呼") > body.index("站务")
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_wall_guest_wall_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLLOW_HOME", str(tmp_path / "hole"))
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.wall"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_WALL_PORT": str(port),
            "HOLLOW_RESERVED_AGENTS": "hollow-监护人",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        h = Hollow(tmp_path / "hole")
        h.append("只有主人的招呼", agent="hollow-监护人")
        deadline = time.time() + 15
        body = ""
        while time.time() < deadline:
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode()
                break
            except Exception:
                time.sleep(0.3)
        assert "第一句话的位置一直留着" in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)
