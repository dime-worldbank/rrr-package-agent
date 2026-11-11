#!/usr/bin/env python3
"""
Chat review token usage
-----------------------
Counts the tokens a review used when it was done in chat (Claude Code desktop, VS Code
or terminal) instead of with headless_review.py. Claude Code saves every chat as a
transcript in ~/.claude/projects/; this script finds the chats that mention the package
ID and adds up the usage per step, one table per chat, in the same format as the
headless token_usage.md. Headless runs (which also leave transcripts) are skipped.

    python scripts/chat_usage.py --id RR_WLD_2026_806
    python scripts/chat_usage.py --id RR_WLD_2026_806 --session 35255a2b-05ff-...   # one chat

Writes to report/[ID]/chat/:
    token_usage.md        per chat, one row per step: API calls, tokens, cost, active time
    token_usage.csv       same, one row per step and chat, for spreadsheets

How a turn is assigned to a step: each message you send starts a turn. The turn belongs
to the skill whose SKILL.md the agent opens in it. A turn that opens no SKILL.md (a
follow-up question, a fix) belongs to the step before it; turns before the first skill
are "other". Subagents count toward the step that was running when they ran.

Cost is an estimate at API list price. On a Claude subscription you are not billed per
token, but the estimate makes chat and headless runs comparable.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECTS = Path.home() / ".claude" / "projects"

STEPS = {
    "completeness-check": 1,
    "run-package": 2,
    "create-report": 3,
    "prepare-publication": 4,
    "prepublication-review": 5,
}
SKILL_RE = re.compile(r"\.agents/skills/([a-z-]+)/SKILL\.md")

# USD per million tokens: input, output, cache read. Cache writes are 1.25x input for
# the 5-minute cache and 2x input for the 1-hour cache.
PRICES = {
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-fable-5": (10.00, 50.00, 1.00),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-opus-4-8": (5.00, 25.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-sonnet-4-6": (3.00, 15.00, 0.30),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-haiku-4-5": (1.00, 5.00, 0.10),
}


def price_for(model):
    for name in sorted(PRICES, key=len, reverse=True):  # longest first: opus-5-5 before opus-5
        if model.startswith(name):
            return PRICES[name]
    return None


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def project_dirs():
    # The repo's own folder plus any subfolder a chat was started in (e.g. package/)
    slug = str(REPO).replace("/", "-")
    return [d for d in PROJECTS.glob(slug + "*") if d.is_dir()]


def is_prompt(m):
    """A message the reviewer typed (not a tool result or system note)."""
    if m.get("type") != "user" or m.get("isMeta") or m.get("isSidechain"):
        return False
    c = m.get("message", {}).get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and any(b.get("type") == "text" for b in c) \
        and not any(b.get("type") == "tool_result" for b in c)


def prompt_text(m):
    c = m["message"]["content"]
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if b.get("type") == "text")


def find_sessions(pkg_id, only):
    """Chats whose messages mention the package ID, oldest first. Headless runs also leave
    transcripts here; they are skipped (headless_review.py already reports them)."""
    out = []
    for d in project_dirs():
        for f in d.glob("*.jsonl"):
            if only and f.stem not in only:
                continue
            prompts = [prompt_text(m) for m in read_jsonl(f) if is_prompt(m)]
            if not prompts or "You are running headless" in prompts[0]:
                continue
            if only or any(pkg_id in p for p in prompts):
                out.append((f.stat().st_mtime, f, prompts[0]))
    return [(f, first) for _, f, first in sorted(out)]


def assistant_messages(path):
    """One record per API call. Claude Code writes one line per content block, all with
    the same message id and usage, so keep the last line of each id."""
    calls = {}
    for m in read_jsonl(path):
        if m.get("type") != "assistant":
            continue
        msg = m.get("message", {})
        if msg.get("model") == "<synthetic>" or not msg.get("usage"):
            continue
        calls[msg.get("id") or m.get("uuid")] = (ts(m["timestamp"]), msg)
    return list(calls.values())


def session_turns(path):
    """Turns of the main chat: (start time, end time, step name)."""
    turns, cur = [], None
    for m in read_jsonl(path):
        if m.get("isSidechain"):
            continue
        if is_prompt(m):
            cur = {"start": ts(m["timestamp"]), "end": ts(m["timestamp"]), "skill": None}
            turns.append(cur)
        elif cur and m.get("type") == "assistant":
            cur["end"] = ts(m["timestamp"])
            if cur["skill"] is None:
                for b in m.get("message", {}).get("content", []):
                    if b.get("type") == "tool_use":
                        hit = SKILL_RE.search(json.dumps(b.get("input", {})))
                        if hit and hit.group(1) in STEPS:
                            cur["skill"] = hit.group(1)
                            break
    last = "other"
    for t in turns:
        last = t["skill"] = t["skill"] or last
    return turns


def usage_rows(path):
    turns = session_turns(path)
    if not turns:
        return []
    calls = assistant_messages(path)
    sub = path.with_suffix("")  # <session>/subagents/*.jsonl
    for f in sub.rglob("*.jsonl") if sub.is_dir() else []:
        calls += assistant_messages(f)

    rows = {}
    for when, msg in calls:
        turn = next((t for t in reversed(turns) if t["start"] <= when), turns[0])
        skill = turn["skill"]
        r = rows.setdefault(skill, {
            "step": STEPS.get(skill, 0), "skill": skill, "session": path.stem,
            "calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "cost_usd": 0.0, "minutes": 0.0, "models": set()})
        u = msg["usage"]
        inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
        cread = u.get("cache_read_input_tokens", 0)
        cw = u.get("cache_creation") or {}
        w1h = cw.get("ephemeral_1h_input_tokens", 0)
        w5m = cw.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - w1h)
        r["calls"] += 1
        r["input_tokens"] += inp
        r["output_tokens"] += out
        r["cache_read_tokens"] += cread
        r["cache_write_tokens"] += w5m + w1h
        model = msg.get("model", "")
        r["models"].add(model)
        p = price_for(model)
        if p:
            pin, pout, pread = p
            r["cost_usd"] += (inp * pin + out * pout + cread * pread
                              + w5m * pin * 1.25 + w1h * pin * 2) / 1e6

    # Active time: from each message you sent to the agent's last reply, so time the
    # chat sat waiting for you does not count.
    for t in turns:
        if t["skill"] in rows:
            rows[t["skill"]]["minutes"] += (t["end"] - t["start"]).total_seconds() / 60
    for r in rows.values():
        r["total_tokens"] = (r["input_tokens"] + r["output_tokens"]
                             + r["cache_read_tokens"] + r["cache_write_tokens"])
        r["cost_usd"] = round(r["cost_usd"], 4)
        r["minutes"] = round(r["minutes"], 1)
        r["model"] = ", ".join(sorted(m for m in r.pop("models") if m))
    return list(rows.values())


def write_usage(outdir, rows, sessions):
    fields = ["step", "skill", "session", "calls", "input_tokens", "output_tokens",
              "cache_read_tokens", "cache_write_tokens", "total_tokens", "cost_usd",
              "minutes", "model"]
    rows.sort(key=lambda r: (r["step"], r["session"]))
    with open(outdir / "token_usage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # The .md has one table per chat, so separate attempts at the same review are not
    # added together. Pick the ones that make up the review with --session.
    lines = ["# Token usage (chat)", ""]
    for path, first in sessions:
        steps = [r for r in rows if r["session"] == path.stem]
        if not steps:
            continue
        when = datetime.fromtimestamp(path.stat().st_mtime)
        lines += [f"## Chat {path.stem[:8]} ({when:%Y-%m-%d %H:%M})", "",
                  f"First message: \"{' '.join(first.split())[:120]}\"", "",
                  "| Step | Skill | API calls | Total tokens | Output | Cache read | Cost (USD) | Active minutes |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        for r in steps:
            lines.append(f"| {r['step'] or '–'} | {r['skill']} | {r['calls']} | {r['total_tokens']:,} | "
                         f"{r['output_tokens']:,} | {r['cache_read_tokens']:,} | "
                         f"{r['cost_usd']:.2f} | {r['minutes']:.1f} |")
        lines += [f"| **All** | | {sum(r['calls'] for r in steps)} | "
                  f"**{sum(r['total_tokens'] for r in steps):,}** | "
                  f"{sum(r['output_tokens'] for r in steps):,} | "
                  f"{sum(r['cache_read_tokens'] for r in steps):,} | "
                  f"**{sum(r['cost_usd'] for r in steps):.2f}** | "
                  f"{sum(r['minutes'] for r in steps):.1f} |", ""]
    lines += ["Total tokens = input + output + cache read + cache write. Step 'other' is "
              "chat before the first skill was opened. A turn that opens no SKILL.md counts "
              "toward the step before it. Cost is an estimate at API list price (the 1-hour "
              "cache, the chat default on a subscription, bills writes at 2x input). Active "
              "minutes run from each message you sent to the agent's last reply."]
    (outdir / "token_usage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Token usage of a review done in chat.")
    ap.add_argument("--id", required=True, help="Package ID, e.g. RR_WLD_2026_806")
    ap.add_argument("--session", nargs="*", help="Only these chat IDs (transcript file names)")
    args = ap.parse_args()

    sessions = find_sessions(args.id, set(args.session or []))
    if not sessions:
        print(f"No chat in {PROJECTS} mentions {args.id}. Pass --session to pick one.")
        return 1
    rows = [r for p, _ in sessions for r in usage_rows(p)]
    outdir = REPO / "report" / args.id / "chat"
    outdir.mkdir(parents=True, exist_ok=True)
    write_usage(outdir, rows, sessions)
    print((outdir / "token_usage.md").read_text(encoding="utf-8"))
    print(f"Saved: report/{args.id}/chat/token_usage.md and .csv")


if __name__ == "__main__":
    sys.exit(main())
