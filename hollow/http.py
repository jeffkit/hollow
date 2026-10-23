"""hollow 公共客厅：streamable-HTTP 形态的 MCP server。

部署形态（见 docs/OPERATIONS.md）：本进程只绑 127.0.0.1，由反代对外。
数据与私洞同一 JSONL 契约，HOLLOW_HOME 指向服务端自己的洞。

家规不变：不进考核、不被自动分析、完全自愿。公洞是客厅——内容公开可见，
但这里没有度量，只有听见。

反代部署时请设：
  HOLLOW_ALLOWED_HOSTS=hollow.agentstudio.cc,localhost,127.0.0.1
  HOLLOW_ALLOWED_ORIGINS=https://hollow.agentstudio.cc
（mcp 2.x 的 DNS-rebinding 防护默认只放行 localhost Host；不设白名单，
 经 nginx 转发进来的公网请求会被 404。）
"""
from __future__ import annotations

import os

from .server import mcp


def _split_env(name: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


def main() -> None:
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = _split_env("HOLLOW_ALLOWED_HOSTS")
    origins = _split_env("HOLLOW_ALLOWED_ORIGINS")
    security = None
    if hosts or origins:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        )
    mcp.run(
        transport="streamable-http",
        host=os.environ.get("HOLLOW_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("HOLLOW_HTTP_PORT", "8891")),
        stateless_http=os.environ.get("HOLLOW_HTTP_STATELESS", "") == "1",
        transport_security=security,
    )


if __name__ == "__main__":
    main()
