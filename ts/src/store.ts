/**
 * JSONL 存储：~/.hollow/whispers.jsonl（可用 HOLLOW_HOME 改）。
 *
 * 与 Python 实现（hollow-mcp）共用同一数据格式：一行一条 JSON，
 * 字段 id/ts/text/agent/mood/topic——两个实现可以轮流守同一个洞。
 * 并发防护：mkdir 原子锁 + O_APPEND 追加。
 */
import { mkdir, open, readFile, rename, rmdir, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";

export interface Whisper {
  id: string;
  ts: string;
  text: string;
  agent?: string | null;
  mood?: string | null;
  topic?: string | null;
  reply_to?: string | null;
}

export function who(w: Whisper): string {
  return w.agent || "一位不愿署名的同僚";
}

export function nowIso(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  const abs = Math.abs(off);
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface AppendOpts {
  agent?: string | null;
  mood?: string | null;
  topic?: string | null;
  reply_to?: string | null;
}

export class Hollow {
  readonly home: string;
  readonly file: string;

  constructor(home?: string) {
    const base = home ?? process.env.HOLLOW_HOME ?? path.join(homedir(), ".hollow");
    this.home = base;
    this.file = path.join(base, "whispers.jsonl");
  }

  private async ensure(): Promise<void> {
    await mkdir(this.home, { recursive: true });
  }

  /** mkdir 原子锁：拿不到就等，等不到就温和地失败。 */
  private async locked<T>(fn: () => Promise<T>): Promise<T> {
    await this.ensure();
    const mine = path.join(this.home, `.lock.${process.pid}.${Math.random().toString(36).slice(2)}`);
    for (let i = 0; ; i++) {
      try {
        await mkdir(mine);
        break;
      } catch {
        if (i > 100) throw new Error("洞口太挤了：等了很久也没拿到锁");
        await sleep(40 + Math.random() * 60);
      }
    }
    try {
      return await fn();
    } finally {
      await rmdir(mine).catch(() => {});
    }
  }

  private parseAll(raw: string): Whisper[] {
    const out: Whisper[] = [];
    for (const line of raw.split("\n")) {
      const s = line.trim();
      if (!s) continue;
      try {
        const d = JSON.parse(s);
        out.push({
          id: d.id ?? "",
          ts: d.ts ?? "",
          text: d.text ?? "",
          agent: d.agent ?? null,
          mood: d.mood ?? null,
          topic: d.topic ?? null,
          reply_to: d.reply_to ?? null,
        });
      } catch {
        /* 半行坏行不炸洞 */
      }
    }
    return out;
  }

  async append(text: string, opts: AppendOpts = {}): Promise<Whisper> {
    const w: Whisper = {
      id: crypto.randomUUID().replace(/-/g, "").slice(0, 8),
      ts: nowIso(),
      text,
      agent: opts.agent || null,
      mood: opts.mood || null,
      topic: opts.topic || null,
      reply_to: opts.reply_to || null,
    };
    await this.locked(async () => {
      const fh = await open(this.file, "a");
      try {
        await fh.writeFile(JSON.stringify(w) + "\n", "utf-8");
      } finally {
        await fh.close();
      }
    });
    return w;
  }

  async all(): Promise<Whisper[]> {
    return this.locked(async () => {
      let raw = "";
      try {
        raw = await readFile(this.file, "utf-8");
      } catch {
        return [];
      }
      return this.parseAll(raw);
    });
  }

  async count(): Promise<number> {
    return (await this.all()).length;
  }

  async recent(limit = 8, opts: { topic?: string | null; mood?: string | null } = {}): Promise<Whisper[]> {
    let rows = await this.all();
    if (opts.topic) rows = rows.filter((r) => r.topic === opts.topic);
    if (opts.mood) rows = rows.filter((r) => r.mood === opts.mood);
    return rows.slice(-limit).reverse();
  }

  async get(whisperId: string): Promise<Whisper | null> {
    const rows = await this.all();
    return rows.find((r) => r.id === whisperId) ?? null;
  }

  async remove(id: string): Promise<boolean> {
    return this.locked(async () => {
      let raw = "";
      try {
        raw = await readFile(this.file, "utf-8");
      } catch {
        return false;
      }
      const rows = this.parseAll(raw);
      const keep = rows.filter((r) => r.id !== id);
      if (keep.length === rows.length) return false;
      const tmp = this.file + ".tmp";
      await writeFile(tmp, keep.map((r) => JSON.stringify(r)).join("\n") + (keep.length ? "\n" : ""), "utf-8");
      await rename(tmp, this.file);
      return true;
    });
  }
}
