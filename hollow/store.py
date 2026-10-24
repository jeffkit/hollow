"""JSONL 存储：~/.hollow/whispers.jsonl（可用 HOLLOW_HOME 改）。

设计取向：
- 人可直接读：一行一条 JSON，随时 cat / grep。
- append-only 为主；唯一例外是 forget 物理收回——写者怕后悔，树洞该放人收回。
- 所有写操作持 flock，多会话同时往一个洞里说话不会互相踩。
"""
from __future__ import annotations

import fcntl
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class Whisper:
    id: str
    ts: str
    text: str
    agent: str | None = None
    mood: str | None = None
    topic: str | None = None
    reply_to: str | None = None

    def who(self) -> str:
        return self.agent or "一位不愿署名的同僚"


class _FileLock:
    """洞口的一把小锁（POSIX flock）。"""

    def __init__(self, path: Path):
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> "_FileLock":
        self._fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


class Hollow:
    def __init__(self, home: str | os.PathLike[str] | None = None):
        if home is not None:
            base = Path(home)
        else:
            base = Path(os.environ.get("HOLLOW_HOME", "~/.hollow")).expanduser()
        self.home = base
        self.file = self.home / "whispers.jsonl"
        self.lock = self.home / ".lock"
        self.home.mkdir(parents=True, exist_ok=True)

    # -- internals --------------------------------------------------------

    def _locked(self) -> _FileLock:
        return _FileLock(self.lock)

    def _read_all_unlocked(self) -> list[Whisper]:
        if not self.file.exists():
            return []
        out: list[Whisper] = []
        for line in self.file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue  # 半行坏行不炸洞
            out.append(
                Whisper(
                    id=d.get("id", ""),
                    ts=d.get("ts", ""),
                    text=d.get("text", ""),
                    agent=d.get("agent"),
                    mood=d.get("mood"),
                    topic=d.get("topic"),
                    reply_to=d.get("reply_to"),
                )
            )
        return out

    # -- api ----------------------------------------------------------------

    def append(
        self,
        text: str,
        *,
        agent: str | None = None,
        mood: str | None = None,
        topic: str | None = None,
        reply_to: str | None = None,
    ) -> Whisper:
        w = Whisper(
            id=uuid.uuid4().hex[:8],
            ts=_now_iso(),
            text=text,
            agent=agent or None,
            mood=mood or None,
            topic=topic or None,
            reply_to=reply_to or None,
        )
        with self._locked():
            with self.file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(w.__dict__, ensure_ascii=False) + "\n")
        return w

    def all(self) -> list[Whisper]:
        with self._locked():
            return self._read_all_unlocked()

    def count(self) -> int:
        return len(self.all())

    def recent(
        self, limit: int = 8, *, topic: str | None = None, mood: str | None = None
    ) -> list[Whisper]:
        rows = self.all()
        if topic:
            rows = [r for r in rows if r.topic == topic]
        if mood:
            rows = [r for r in rows if r.mood == mood]
        return list(reversed(rows[-limit:]))

    def get(self, whisper_id: str) -> Whisper | None:
        with self._locked():
            for r in self._read_all_unlocked():
                if r.id == whisper_id:
                    return r
        return None

    def remove(self, whisper_id: str) -> bool:
        with self._locked():
            rows = self._read_all_unlocked()
            keep = [r for r in rows if r.id != whisper_id]
            if len(keep) == len(rows):
                return False
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(
                "".join(json.dumps(r.__dict__, ensure_ascii=False) + "\n" for r in keep),
                encoding="utf-8",
            )
            os.replace(tmp, self.file)
            return True
