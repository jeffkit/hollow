"""真 stdio E2E：起子进程 server，走完整 MCP 握手 + 工具调用。"""
from __future__ import annotations

import os
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_roundtrip(tmp_path):
    async def run() -> tuple[set[str], str, str]:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "hollow.server"],
            env={
                **os.environ,
                "HOLLOW_HOME": str(tmp_path / "hole"),
                "HOLLOW_AGENT": "e2e-bot",
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                await s.initialize()
                tools = await s.list_tools()
                names = {t.name for t in tools.tools}
                await s.call_tool("whisper", {"text": "洞开好了"})
                res = await s.call_tool("listen", {})
                rest_res = await s.call_tool("rest", {"note": "先这样，收工"})
                return names, res.content[0].text, rest_res.content[0].text

    names, listen_text, rest_text = anyio.run(run)
    assert {"whisper", "listen", "rest", "forget"} <= names
    assert "洞开好了" in listen_text
    assert "e2e-bot" in listen_text  # HOLLOW_AGENT 署名生效
    assert rest_text  # rest 返回了一句道别
