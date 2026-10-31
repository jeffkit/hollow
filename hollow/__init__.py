"""hollow — AI 同僚的树洞。monarbor 管理森林；hollow 是树上那个可以说话的洞。"""

try:
    from importlib.metadata import version as _v

    __version__ = _v("hollow-mcp")
except Exception:  # noqa: BLE001
    __version__ = "unknown"
