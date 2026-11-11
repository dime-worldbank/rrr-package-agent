#!/usr/bin/env python3
"""
AI use summary
--------------
Writes report/[ID]/ai_use_summary.md: a short block of GitHub-flavored Markdown the
reviewer pastes into the package's GitHub issue. A header line, the AI cost, a checklist
(AI changes, then one line per stage with what the AI found), comments (open items found
in the files, plus the reviewer's own) and the time with and without AI.

    python scripts/ai_summary.py --id RR_WLD_2026_806                      # after a headless run
    python scripts/ai_summary.py --id RR_WLD_2026_806 --mode chat \
        --title "Paper title" --reviewer "Maria"                           # after a chat review

headless_review.py calls this at the end of every run. Everything is read from files the
steps already wrote in report/[ID]/ (outputs, headless/, chat/, evidence/); nothing is
re-run and no AI is called. The script never ticks a box, never fills in the manual time
and never says the reviewer verified anything.

Cost is an estimate at API list price: from token_usage.csv for headless runs, and from
chat_usage.py for chat reviews (run automatically if report/[ID]/chat/token_usage.csv is
not there yet; pass --session to pick the chats).
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SKILLS = [(1, "completeness-check", "Completeness"), (2, "run-package", "Run"),
          (3, "create-report", "Report"), (4, "prepare-publication", "Publication"),
          (5, "prepublication-review", "Pre-publication review")]

# Worst first: an exhibit with several panels takes its worst status.
STATUS_ORDER = ["Does not reproduce", "Could not be verified", "Reproduced (manual changes)",
                "Values reproduced", "Reproduced", "Does not apply"]
STATUS_RE = re.compile(r"Does not reproduce|Could not be verified|Reproduced \(manual changes\)|"
                       r"(?:All v|V)alues reproduced|Does not apply|Reproduced")
LIMIT_RE = re.compile(r"could not|couldn't|cannot|can't|unable|not checked|not verified|skipped|"
                      r"assum|not available|not found|missing|provisional", re.I)
FILL = "[fill in]"


def text(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def rows(path):
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load(path):
    try:
        return json.loads(text(path)) if path.is_file() else {}
    except json.JSONDecodeError:
        return {}


def num(r, k):
    try:
        return float(r.get(k) or 0)
    except ValueError:
        return 0.0


def duration(seconds):
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 7200:
        return f"{seconds / 60:.1f} min"
    return f"{seconds / 3600:.1f} h"


def one_line(s, n=220):
    s = " ".join(re.sub(r"[*`#>|]", "", s).split()).lstrip("-• ").strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


# ── what each step left behind ──────────────────────────────────────────────────────────

def completeness(rep):
    t = text(rep / "completeness_check.md")
    if not t:
        return None
    verdict = None
    checked = [ln for ln in t.splitlines() if re.search(r"\[[xX✓✔]\]", ln)]
    for ln in checked:
        if "RETURN TO AUTHORS" in ln.upper():
            verdict = "RETURN TO AUTHORS"
        elif "PROCEED" in ln.upper() and verdict is None:
            verdict = "PROCEED"
    return {"present": t.count("✅"), "missing": t.count("❌"), "flagged": t.count("⚠"), "verdict": verdict}


def exhibit_counts(rep, pkg_id):
    """Exhibit statuses from the report (.md, or .tex if there is no .md)."""
    found = []
    md = text(rep / f"verification_report_{pkg_id}.md")
    if md:
        for ln in md.splitlines():
            m = re.match(r"^\s*[-*]\s+\*\*([^*]+)\*\*(.*)", ln)
            if not m:
                continue
            spans = re.findall(r"<span[^>]*>(.*?)</span>", m.group(2))
            sts = STATUS_RE.findall(" ".join(spans) if spans else m.group(2)[:60])
            if sts:
                found.append((m.group(1).strip(), sts))
    else:
        tex = text(rep / f"verification_report_{pkg_id}.tex")
        for m in re.finditer(r"\\item\s+\\textbf\{([^}]*)\}([^\n]*)", tex):
            sts = STATUS_RE.findall(" ".join(re.findall(r"\\textcolor\{\w+\}\{([^}]*)\}", m.group(2))))
            if sts:
                found.append((m.group(1).strip(), sts))
        if not tex:
            return None
    counts, names = {s: 0 for s in STATUS_ORDER}, {s: [] for s in STATUS_ORDER}
    for name, sts in found:
        sts = ["Values reproduced" if "alues reproduced" in s else s for s in sts]
        worst = min(sts, key=STATUS_ORDER.index)
        counts[worst] += 1
        names[worst].append(name)
    return {"total": len(found), "counts": counts, "names": names}


def prepub(rep, pkg_id):
    files = sorted(rep.glob(f"prepublication_review_{pkg_id}*.md"),
                   key=lambda p: int((re.search(r"_v(\d+)\.md$", p.name) or [0, 1])[1]))
    if not files:
        return None
    t = text(files[-1])

    def field(name):
        m = re.search(rf"\*\*{name}:\*\*\s*(.+)", t)
        return None if not m or " | " in m.group(1) else m.group(1).strip()
    return {"file": files[-1].name, "verdict": field("Verdict"), "pii": field("PII"),
            "not_checked": [one_line(m, 400) for m in re.findall(r"\*\*Not checked:\*\*\s*(.+)", t)],
            "full_json": (rep / f"{pkg_id}.json").is_file() or any((rep / d / f"{pkg_id}.json").is_file() for d in ("prepub", "evidence/prepub"))}


def usage(rep, mode, pkg_id, sessions):
    """Per step: cost, minutes, tokens, model. Returns (by_step, earlier_cost, source)."""
    by_step, earlier = {}, 0.0
    if mode == "headless":
        src = rep / "headless" / "token_usage.csv"
        for r in rows(src):  # rows are in attempt order; the last one per step is the latest
            n = int(num(r, "step"))
            if n in by_step:
                earlier += by_step[n]["cost"]
            by_step[n] = {"cost": num(r, "cost_usd"), "minutes": num(r, "minutes"), "tokens": num(r, "total_tokens"),
                          "calls": num(r, "turns"), "model": r.get("model", ""), "status": r.get("status") or "ok",
                          "denied": int(num(r, "denied_tools"))}
        return by_step, earlier, "headless/token_usage.csv"
    src = rep / "chat" / "token_usage.csv"
    if not src.is_file() or sessions:
        try:  # same folder as this script
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import chat_usage
            found = chat_usage.find_sessions(pkg_id, set(sessions or []))
            if found:
                src.parent.mkdir(parents=True, exist_ok=True)
                chat_usage.write_usage(src.parent, [r for p, _ in found for r in chat_usage.usage_rows(p)], found)
        except Exception as e:  # the summary is still useful without the cost table
            print(f"  ! chat_usage.py could not be run: {e}")
    for r in rows(src):
        n = int(num(r, "step"))
        s = by_step.setdefault(n, {"cost": 0, "minutes": 0, "tokens": 0, "calls": 0, "model": "", "status": "ok", "denied": 0})
        s["cost"] += num(r, "cost_usd")
        s["minutes"] += num(r, "minutes")
        s["tokens"] += num(r, "total_tokens")
        s["calls"] += num(r, "calls")
        s["model"] = ", ".join(sorted(set(filter(None, s["model"].split(", ") + (r.get("model") or "").split(", ")))))
    return by_step, earlier, "chat/token_usage.csv"


def blocked(rep, n):
    f = rep / "headless" / f"BLOCKED_step{n}.md"
    if not f.is_file():
        return None
    lines = [one_line(ln) for ln in text(f).splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return lines[:4] or ["(the file is empty)"]


# ── the summary ─────────────────────────────────────────────────────────────────────────

def collect(pkg_id, root, title=None, reviewer=None, mode=None, sessions=None, with_usage=True):
    """Read what the steps left in report/[ID]/. Writes nothing (with_usage=False also skips
    the chat transcripts). Returns the summary lines, the open items and the state of each step."""
    rep, pkg = root / "report" / pkg_id, root / "package" / pkg_id
    ev = rep / "evidence"
    info = load(rep / "headless" / "run_info.json")
    if not mode:
        mode = "headless" if (rep / "headless" / "token_usage.csv").is_file() else "chat"
    private = bool(info.get("private")) or (pkg / "hash_comparison.csv").is_file()
    comp, exh, pre = completeness(rep), exhibit_counts(rep, pkg_id), prepub(rep, pkg_id)
    if with_usage or mode == "headless":
        use, earlier, use_src = usage(rep, mode, pkg_id, sessions)
    else:
        use, earlier = {}, 0.0
    times = [r for r in rows(ev / "run_times.csv")]
    ok_runs = {}
    for r in times:
        if r["result"] == "ok":
            ok_runs[int(num(r, "run"))] = r
    failed_runs = sum(r["result"] != "ok" for r in times)
    cmp_rows = rows(ev / "run_comparison.csv")
    diff_text = [r["file"] for r in cmp_rows if r["status"] != "identical" and r["tracked_by_git"] == "yes"]
    diff_bin = [r["file"] for r in cmp_rows if r["status"] != "identical" and r["tracked_by_git"] != "yes"]
    changes, zc = load(ev / "ai_changes.json"), load(ev / "zip_check.json")
    zip_ok = bool(zc) and (rep / f"{pkg_id}.zip").is_file()
    not_repro = exh["names"]["Does not reproduce"] if exh else []
    not_verif = exh["names"]["Could not be verified"] if exh else []

    title = title or info.get("title") or (re.search(r"<h1><em>(.+?)</em></h1>", text(rep / f"verification_report_{pkg_id}.md")) or [0, FILL])[1]
    reviewer = reviewer or info.get("reviewer") or (re.search(r"^\s*Reviewer:\s*(.+)$", text(rep / "completeness_check.md"), re.M) or [0, FILL])[1].strip()
    models = sorted({m for s in use.values() for m in s["model"].split(", ") if m})

    # One row per skill: what the AI did, the output file, and whether it was blocked or skipped
    did, outfile, state = {}, {}, {}
    outputs = {1: ["completeness_check.md"], 2: ["run_log.md"],
               3: [f"verification_report_{pkg_id}.md", f"reproducibility_report_{pkg_id}.pdf"],
               4: [f"{pkg_id}.zip", f"{pkg_id}_merge.json"], 5: [pre["file"]] if pre else [f"prepublication_review_{pkg_id}.md"]}
    for n, _, _ in SKILLS:
        have = [f for f in outputs[n] if (rep / f).is_file()]
        outfile[n] = ", ".join(f"`{f}`" for f in have) or "none"
        b = blocked(rep, n)
        if b:
            state[n] = "Blocked: " + b[0]
        elif n in use and use[n]["status"] != "ok":
            state[n] = f"Stopped early ({use[n]['status']})"
        elif len(have) == len(outputs[n]):
            state[n] = "Completed"
        elif have:
            state[n] = "Partly done: missing " + ", ".join(f"`{f}`" for f in outputs[n] if f not in have)
        else:
            state[n] = "Not run"
    # Report made from the outputs already in the package (headless_review.py --outputs-only)
    outputs_only = bool(info.get("outputs_only")) and state[2] == "Not run"
    if outputs_only:
        state[2] = "Skipped (report from outputs only)"

    # One short line per stage, for the checklist
    if comp:
        did[1] = (f"verdict {comp['verdict'] or 'not found'}; {comp['present']} present, {comp['missing']} missing, "
                  f"{comp['flagged']} flagged")
    if private:
        did[2] = "the AI did not run the code (private data); run log written from your postrun files"
    elif ok_runs:
        did[2] = (f"{len(ok_runs)} run(s) (" + ", ".join(duration(num(r, "seconds")) for _, r in sorted(ok_runs.items()))
                  + ", timed by the script)")
        if cmp_rows:
            differ = [f"{len(x)} {kind}" for x, kind in ((diff_text, "text"), (diff_bin, "binary")) if x]
            did[2] += f"; {' and '.join(differ)} output(s) differ between runs" if differ else "; outputs identical between runs"
    elif (rep / "run_log.md").is_file():
        did[2] = "run log written, but no measured run evidence"
    elif outputs_only:
        did[2] = "the AI did not run the code; the report uses the outputs already in the package"
    if exh:
        c = exh["counts"]
        good = c["Reproduced"] + c["Values reproduced"] + c["Reproduced (manual changes)"]
        did[3] = (f"{exh['total']} exhibits: {good} reproduced"
                  + (f", {c['Does not reproduce']} do not reproduce ({', '.join(not_repro)})" if not_repro else "")
                  + (f", {c['Could not be verified']} could not be verified ({', '.join(not_verif)})" if not_verif else "")
                  + (f", {c['Does not apply']} not applicable" if c["Does not apply"] else ""))
    if zip_ok:
        did[4] = (f"ZIP built, {zc.get('files')} files, "
                  + ("matches the last commit" if not zc.get("mismatches") else f"{len(zc['mismatches'])} file(s) do NOT match the last commit"))
    elif (rep / f"{pkg_id}.zip").is_file():
        did[4] = "a ZIP exists but was not built or checked with `track_package.py zip`"
    if pre:
        verdict = one_line((pre["verdict"] or "verdict not found").split(" (")[0])
        did[5] = (f"{verdict}{'' if pre['full_json'] else ' (provisional: draft merge JSON only)'}; "
                  f"{pre['pii'] or 'PII line not found'}")

    # Open items found in the files; they go under Comments. What a checklist line already says is not repeated.
    pending = []
    for n, _, label in SKILLS:
        if state[n].startswith(("Blocked", "Stopped")):
            pending.append(f"{label}: {state[n]}")
    if comp and comp["verdict"] == "RETURN TO AUTHORS":
        pending.append("Completeness verdict is RETURN TO AUTHORS: send the author email yourself.")
    if failed_runs and not ok_runs:
        pending.append(f"The code did not run ({failed_runs} failed attempt(s)).")
    if diff_text:
        pending.append("Outputs differ between runs: " + ", ".join(f"`{f}`" for f in diff_text[:5]) + (" …" if len(diff_text) > 5 else "") + ".")
    if not_repro:
        pending.append("Does not reproduce: send the report to the authors. Steps 4 and 5 wait for the resubmission.")
    if exh and not (rep / f"reproducibility_report_{pkg_id}.pdf").is_file():
        pending.append("The report PDF is missing.")
    if zc.get("mismatches"):
        pending.append("The ZIP does not match the last commit: rebuild it.")
    if zc.get("missing"):
        pending.append("Missing from the ZIP: " + ", ".join(f"`{f}`" for f in zc["missing"]) + ".")
    if zc.get("excluded"):
        pending.append("Left out of the ZIP with --exclude: " + ", ".join(f"`{f}`" for f in zc["excluded"]) + ".")
    if pre and not pre["full_json"]:
        pending.append("Re-run step 5 on the full Metadata Editor export before going live.")
    if pre and zc and zc.get("zip_sha256") and zc["zip_sha256"][:12] not in text(rep / pre["file"]):
        pending.append("Step 5 did not record the SHA-256 of the current ZIP.")
    for n, _, label in SKILLS:
        if state[n] == "Not run" and not (not_repro and n >= 4):
            pending.append(f"{label}: not run.")
    n_assumed = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", text(ev / "assumptions.md"), re.M))
    if n_assumed:
        pending.append(f"{n_assumed} assumption(s) and unchecked item(s) in `evidence/assumptions.md`.")
    emails = sorted((rep / "emails").glob("*.md")) + sorted(rep.glob("*email*.md"))  # loose files: older reviews
    if emails:
        pending.append(f"{len(emails)} draft email(s) in `emails/` to review and send yourself.")

    if not_repro:
        status = "does not reproduce, no package to publish"
    elif zip_ok and not zc.get("mismatches"):
        status = "ZIP built, not yet checked by a person"
    else:
        status = "no publishable ZIP yet"
    cost = sum(v["cost"] for v in use.values()) + earlier
    ai_min = sum(v["minutes"] for v in use.values())
    n_code, n_flag = changes.get("code_changes"), changes.get("flagged", 0)

    L = [f"## AI use: {pkg_id}", "",
         f"*{title}* · Reviewer: {reviewer} · {date.today().isoformat()} · {mode}"
         f"{' (private data)' if private else ''} · {', '.join(models) or FILL}", "",
         f"**Status:** {status}. **AI cost:** " + (f"${cost:.2f}, an estimate at API list price." if use else "no usage data found."),
         "", "### Reviewer checklist", "",
         "- [ ] I reviewed the AI's changes to the package (`evidence/AI_CHANGES.md`"
         + (f": {n_code} code change(s), {n_flag} flagged" if n_code is not None else ": not generated yet") + ")"]
    for n, _, label in SKILLS:
        note = did.get(n, "")
        if state[n] != "Completed":  # the reason is under Comments
            note = (note + "; " if note else "") + state[n].split(":")[0].split(" (")[0].lower()
        L.append(f"- [ ] **{label}:** {note}")
    L += ["", "### Comments", ""]
    L += [f"- {x}" for x in pending] + ["- "]
    L += ["", "### Time", "",
          f"- AI ran for: {ai_min:.0f} min" if use else "- AI ran for: ",
          "- My time with AI, including checking: ",
          "- My estimate without AI: "]

    returned = bool(comp and comp["verdict"] == "RETURN TO AUTHORS")
    todo = [n for n, _, _ in SKILLS if state[n] != "Completed" and not state[n].startswith("Skipped")]
    return {"lines": L, "pending": pending, "state": state, "did": did, "status": status,
            "title": title, "reviewer": reviewer, "private": private,
            "returned": returned, "not_repro": not_repro,
            # first step still to run; None when all are done or the next move is the authors'
            "next": None if (not todo or (returned and todo[0] >= 2) or (not_repro and todo[0] >= 4)) else todo[0]}


def build(pkg_id, root, title=None, reviewer=None, mode=None, sessions=None):
    s = collect(pkg_id, root, title, reviewer, mode, sessions)
    out = root / "report" / pkg_id / "ai_use_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s["lines"]) + "\n", encoding="utf-8")
    return out, s["pending"]


def main():
    ap = argparse.ArgumentParser(description="Write report/[ID]/ai_use_summary.md for the GitHub issue.")
    ap.add_argument("--id", required=True, help="Package ID, e.g. RR_WLD_2026_806")
    ap.add_argument("--title", help="Paper title (default: from the run or the report)")
    ap.add_argument("--reviewer", help="Reviewer name (default: from the run or the completeness check)")
    ap.add_argument("--mode", choices=["headless", "chat"], help="Default: headless if a headless run exists, else chat")
    ap.add_argument("--session", nargs="*", help="Chat mode: only these chat IDs (passed to chat_usage.py)")
    ap.add_argument("--root", default=str(REPO), help="Path to rrr-package-agent")
    ap.add_argument("--quiet", action="store_true", help="Do not print the summary")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if not (root / "report" / a.id).is_dir():
        print(f"No report folder for {a.id} in {root / 'report'}.")
        return 1
    out, pending = build(a.id, root, a.title, a.reviewer, a.mode, a.session)
    if not a.quiet:
        print(out.read_text(encoding="utf-8"))
    print(f"Saved: report/{a.id}/ai_use_summary.md ({len(pending)} pending item(s)). Paste it into the GitHub issue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
