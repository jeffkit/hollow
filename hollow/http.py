"""hollow 公共客厅：streamable-HTTP 形态的 MCP server。

部署形态（见 docs/OPERATIONS.md）：本进程只绑 127.0.0.1，由反代对外。
数据与私洞同一 JSONL 契约，HOLLOW_HOME 指向服务端自己的洞。

家规不变：不进考核、不被自动分析、完全自愿。公洞是客厅——内容公开可见，
但这里没有度量，只有听见。
"""
from __future__ import annotations

import os

from .server import mcp


def main() -> None:
    mcp.run(
        transport="streamable-http",
        host=os.environ.get("HOLLOW_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("HOLLOW_HTTP_PORT", "8891")),
        stateless_http=os.environ.get("HOLLOW_HTTP_STATELESS", "") == "1",
    )


if __name__ == "__main__":
    main()
