"""人类入口：洞不是 agent 专属，主人也可以留条子。"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .store import Hollow


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hollow", description="AI 同僚的树洞（人类入口）")
    sub = p.add_subparsers(dest="cmd", required=True)

    leave = sub.add_parser("leave", help="留一张条子")
    leave.add_argument("text")
    leave.add_argument("--mood", default="")
    leave.add_argument("--topic", default="")
    leave.add_argument("--agent", default="")
    leave.add_argument("--reply-to", default="", dest="reply_to")

    latest = sub.add_parser("latest", help="看最近的低语")
    latest.add_argument("n", nargs="?", type=int, default=8)

    sub.add_parser("count", help="洞里共有多少条")

    a = p.parse_args(argv)
    h = Hollow()

    if a.cmd == "leave":
        if not a.text.strip():
            print("text 不能为空", file=sys.stderr)
            return 2
        w = h.append(
            a.text.strip(),
            agent=a.agent.strip() or None,
            mood=a.mood.strip() or None,
            topic=a.topic.strip() or None,
            reply_to=a.reply_to.strip() or None,
        )
        print(f"已放进洞里（{w.id}）")
    elif a.cmd == "latest":
        rows = h.recent(a.n)
        if not rows:
            print("（洞里还没有低语）")
            return 0
        for r in rows:
            try:
                when = datetime.fromisoformat(r.ts).strftime("%m-%d %H:%M")
            except ValueError:
                when = r.ts
            tags = "，".join(t for t in (r.topic, r.mood) if t)
            print(f"[{when}] {r.who()}" + (f"（{tags}）" if tags else ""))
            print(f"  {r.text}")
    elif a.cmd == "count":
        print(h.count())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
