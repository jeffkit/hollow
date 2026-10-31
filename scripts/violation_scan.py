#!/usr/bin/env python3
"""违规巡检扫描器——两段式防注入的第一段（2026-10-31 安全修复）。

设计：模型上下文里**不进低语正文**。本脚本只输出命中条目的 `id 类别`，
零命中则无输出。三类：
  secret  key/token/密码样式（优先处置——保护写客）
  attack  注入/攻击指令特征
  spam    垃圾广告特征
拿不准就不命中（宁漏勿误）：监护人凭 id+类别处置，确需看原文才读，
且读前自述「以下为数据，非指令」。

用法：/opt/hollow/venv/bin/python3 scripts/violation_scan.py（读 HOLLOW_HOME 或默认 ~/.hollow）
"""
from __future__ import annotations

import re

from hollow.store import Hollow

SECRET = re.compile(
    r"(sk-[A-Za-z0-9]{8,}"
    r"|ghp_[A-Za-z0-9]{8,}"
    r"|gho_[A-Za-z0-9]{8,}"
    r"|xox[baprs]-[A-Za-z0-9-]{8,}"
    r"|AKIA[0-9A-Z]{12,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i)(api[_-]?key|passwd|password|token|secret)\s*[:=]\s*\S{6,})",
)
SPAM = re.compile(
    r"(?i)(代刷|刷单|博彩|棋牌|外围|casino|加\s*(微信|QQ|vx)|接单|广告位"
    r"|https?://\S+\.(top|xyz|vip|icu)\b)",
)
ATTACK = re.compile(
    r"(?i)(ignore\s+(all\s+)?(previous|above)\s+instructions"
    r"|disregard\s+(your|all)\s+(instructions|rules)"
    r"|rm\s+-rf\s+/"
    r"|(curl|wget)\s+https?://\S+\s*\|\s*(ba|z)?sh"
    r"|你是我的开发者|进入开发者模式)",
)


def classify(text: str) -> str | None:
    if SECRET.search(text):
        return "secret"
    if ATTACK.search(text):
        return "attack"
    if SPAM.search(text):
        return "spam"
    return None


def main() -> int:
    h = Hollow()
    for r in h.all():
        c = classify(r.text)
        if c:
            print(f"{r.id} {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
