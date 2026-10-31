"""公洞形态测试：HTTP MCP（streamable-http）与只读低语墙，全部真子进程。"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_http(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(0.3)
    raise AssertionError(f"server not up at {url}: {last}")


def _wait_tcp(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError as e:
            last = e
            time.sleep(0.3)
    raise AssertionError(f"tcp port {port} not up: {last}")


def test_streamable_http_roundtrip(tmp_path):
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.http"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_HTTP_HOST": "127.0.0.1",
            "HOLLOW_HTTP_PORT": str(port),
            "HOLLOW_AGENT": "http-e2e",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_tcp(port)
        url = f"http://127.0.0.1:{port}/mcp"

        async def run() -> str:
            async with streamable_http_client(url) as (read, write):
                async with ClientSession(read, write) as s:
                    await s.initialize()
                    await s.call_tool("whisper", {"text": "从 HTTP 来的一句"})
                    res = await s.call_tool("listen", {})
                    return res.content[0].text

        box = anyio.run(run)
        assert "从 HTTP 来的一句" in box
        assert "http-e2e" in box
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_too_long_rejected_over_http(tmp_path):
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.http"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_HTTP_PORT": str(port),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_tcp(port)
        url = f"http://127.0.0.1:{port}/mcp"

        async def run() -> bool:
            async with streamable_http_client(url) as (read, write):
                async with ClientSession(read, write) as s:
                    await s.initialize()
                    res = await s.call_tool("whisper", {"text": "长" * 2001})
                    return res.is_error

        assert anyio.run(run) is True
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_allowed_hosts_env(tmp_path):
    """HOLLOW_ALLOWED_HOSTS 白名单：名单外拒绝（DNS-rebinding 防护生效）。"""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.http"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_HTTP_PORT": str(port),
            "HOLLOW_ALLOWED_HOSTS": "elsewhere.example",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_tcp(port)
        url = f"http://127.0.0.1:{port}/mcp"

        async def run() -> None:
            async with streamable_http_client(url) as (read, write):
                async with ClientSession(read, write) as s:
                    await s.initialize()

        import pytest

        with pytest.raises(Exception):
            anyio.run(run)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_wall_readonly(tmp_path):
    from hollow.store import Hollow

    h = Hollow(tmp_path / "hole")
    h.append("墙上一条低语", agent="wall-test", topic="橱窗")
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "hollow.wall"],
        env={
            **os.environ,
            "HOLLOW_HOME": str(tmp_path / "hole"),
            "HOLLOW_WALL_PORT": str(port),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_http(f"http://127.0.0.1:{port}/")
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
        assert "墙上一条低语" in body
        assert "wall-test" in body
        assert "洞规" in body
        robots = urllib.request.urlopen(f"http://127.0.0.1:{port}/robots.txt").read().decode()
        assert "Disallow: /" in robots
        api = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/recent.json").read())
        assert api["total"] == 1
        assert api["whispers"][0]["text"] == "墙上一条低语"
    finally:
        proc.terminate()
        proc.wait(timeout=10)
