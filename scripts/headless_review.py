#!/usr/bin/env python3
"""
Headless review runner
----------------------
Runs the five skills one after another with Claude Code in headless mode
(`claude -p`), one fresh session per skill. Each skill reads what the previous
one saved in report/[ID]/, so nothing depends on chat history.

    python scripts/headless_review.py 806 --title "Measuring Human Capital Over the Life Cycle"

    python scripts/headless_review.py 806 --status        # where the review stands; runs nothing
    python scripts/headless_review.py 806 --steps next    # resume from the first unfinished step
    python scripts/headless_review.py 806 --steps 3       # one step
    python scripts/headless_review.py 806 --steps 3-5     # a range

The ID can be the full package ID or just its number, when one folder in package/ ends with it.
Only the first run needs --title. The reviewer comes from --reviewer, else RRR_REVIEWER, else
`git config user.name`; the software is detected from the code files unless --software says
otherwise. All of it (and --private) is saved in report/[ID]/headless/run_info.json and reused
by later runs, so a resume needs only the ID.

Writes to report/[ID]/headless/:
    stepN_<skill>.jsonl   full transcript (every tool call and result)
    stepN_<skill>.md      the agent's final summary for that step
    BLOCKED_stepN.md      why step N could not run or finish, and what the reviewer must do
    token_usage.md        one row per step: turns, tokens, cost, time
    token_usage.csv       every attempt at every step, for spreadsheets
and, at the end of every run, report/[ID]/ai_use_summary.md (scripts/ai_summary.py), the
block the reviewer pastes into the GitHub issue.

Before each step the script checks that the outputs of the step before exist. A step that
is blocked, crashes, times out or goes over budget stops the run (exit code 1); fix the
cause and resume with --steps. A package that does not reproduce always stops before step 4.
When a step is run again, its old transcript, summary and BLOCKED file are kept under a
time-stamped name. What the agent changes in package/[ID]/ is tracked in a local Git repo
whose history lives in report/[ID]/evidence/ (see run-package/scripts/track_package.py).

Run from the rrr-package-agent folder. Needs the `claude` CLI, logged in.
The agent never sends email, pushes, or publishes: those stay with the reviewer.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import ai_summary  # same folder

REPO = Path(__file__).resolve().parent.parent
TRACK = REPO / ".agents/skills/run-package/scripts/track_package.py"

STEPS = {
    1: ("completeness-check", "Step 1 (completeness check)"),
    2: ("run-package", "Step 2 (run package)"),
    3: ("create-report", "Step 3 (create report)"),
    4: ("prepare-publication", "Step 4 (prepare publication)"),
    5: ("prepublication-review", "Step 5 (pre-publication review)"),
}

# Tools the agent may use without asking. Headless mode cannot show a permission
# prompt, so anything not allowed is refused. Bash is allowed in general because
# per-command rules refuse ordinary forms like "cd x && ...", "VAR=... cmd" or sed;
# the blocks below still win over it.
# Even with Bash allowed, the default mode still refuses commands its safety checks
# can't analyse ($VAR, two cd's, cp -p, > redirects): 29 refusals in RR_WLD_2026_806.
# "auto" mode has a classifier decide those instead. The sandbox would also stop the
# refusals, but it blocks network access and the R/renv cache in ~/Library, which step 2 needs.
PERMISSION_MODE = "auto"

# Each step finishes in minutes, so the 5-minute prompt cache is enough. The 1-hour
# cache (the default on a subscription) bills writes at 2x input instead of 1.25x, and
# cache writes were half the cost of RR_WLD_2026_806.
CACHE_TTL = "5m"

ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "TodoWrite", "Bash"]
DISALLOWED = ["Bash(git push:*)", "Bash(git remote:*)", "Bash(git clone:*)", "Bash(curl:*)",
              "Bash(wget:*)", "Bash(gh:*)", "Bash(ssh:*)", "Bash(scp:*)", "Bash(rsync:*)",
              "Bash(sudo:*)", "WebFetch", "WebSearch"]

HEADLESS_RULES = """
You are running headless: nobody can answer questions or approve anything during this run.
- Do not ask the reviewer anything. Use the details below. Where the skill says to ask,
  make the most reasonable choice, write it down and continue.
- Assumptions, and anything you did not do or could not check, go in one place only:
  report/{id}/evidence/assumptions.md. Append a section "## Step {n}" with short bullets; do not
  put an Assumptions or "Not done" section in the checklist, run log, report or review.
- The top level of report/{id}/ holds only the files this prompt and the skill name. Do not write
  any other document there (no step log, no "what was done" file): what you changed is already in
  the Git history. Working files you need to keep (install logs, copies of original outputs,
  scan results) go in report/{id}/evidence/.
- Never send, upload, publish or push anything. Draft emails as files only, all of them in
  report/{id}/emails/ with the numbered names given here or in the skill.
- Work only inside this repository: package/{id}/, report/{id}/ and, for step 5's log row,
  report/prepublication_log.md. Never delete anything outside package/{id}/ and report/{id}/.
- If something blocks the step (missing file, failed run), write what blocked it and what
  the reviewer must do in report/{id}/headless/BLOCKED_step{n}.md, then stop.
- Never report something you did not do or could not check as done. Say it was skipped, and why.
- Every change you make inside package/{id}/ must be in a commit made with
  .agents/skills/run-package/scripts/track_package.py before you finish, with a --note saying
  what changed and why. Never delete, move or edit the .git file in package/{id}/ or anything
  in report/{id}/evidence/, and never add a Git remote.
- Keep the context small: every file you open is re-read on every later turn. Read PDFs as
  text (`pdftotext -layout`, `pdfinfo`) and compare images by checksum (`shasum`) first. Open
  a PDF page or image only when the text or checksum is not enough, and never open the same
  one twice.
- End with a short summary (under 15 lines): files written, verdict, and what a human
  must check or do before the next step.

Date: {date}
Package ID: {id}
Paper title: {title}
Software: {software}
Reviewer: {reviewer}
Data: {data}
"""

STEP_TASKS = {
    1: """Read .agents/skills/completeness-check/SKILL.md in full and follow it for package {id}.
The submission is in package/{id}/. If it is a ZIP, extract it into package/{id}/ first and
review the extracted files. Save the checklist as report/{id}/completeness_check.md and, if
anything is missing, the draft author email as report/{id}/emails/1_missing_items.md.""",
    2: """Read .agents/skills/run-package/SKILL.md in full and follow it for package {id}.
Read report/{id}/completeness_check.md first. If its verdict is RETURN TO AUTHORS, write
BLOCKED_step2.md and stop. Otherwise set up the environment and use track_package.py as the
skill describes: `init` for local Git, `run --n 1` and `run --n 2` for the two runs (it times
them, saves the log and the SHA-256 manifest and commits), `commit` for each code fix on its
own, and `compare` for stability. Do not run git init, time the runs or commit by hand. Take
the runtimes from report/{id}/evidence/run_times.csv, never from your own estimate.
Save the Run Log as report/{id}/run_log.md and the confirmation email draft as
report/{id}/emails/2_run_confirmation.md.""",
    3: """Read .agents/skills/create-report/SKILL.md in full and follow it for package {id}.
Use report/{id}/completeness_check.md and report/{id}/run_log.md. Compare every exhibit in
the manuscript with the outputs from the run. For every exhibit that does not reproduce, make
the Code / Paper comparison images in report/{id}/graphics/ as the skill's "Making the
comparison screenshots" section describes, and show them side by side in the report.
Write the report in the formats the skill asks for and export the PDF to report/{id}/reproducibility_report_{id}.pdf as the skill describes,
then check its layout once as the skill describes. If any exhibit does not reproduce, draft the email
that sends the report to the authors as report/{id}/emails/3_report_to_authors.md.
Do not change anything in package/{id}/.""",
    4: """Read .agents/skills/prepare-publication/SKILL.md in full and follow it for package {id}.
Use the outputs of steps 1-3 in report/{id}/. Commit each action with track_package.py
`commit --label step4-...` as the skill describes, build the ZIP with track_package.py `zip`
(never by hand) and write report/{id}/{id}_merge.json in the format the skill describes.
Do not delete non-public data: leave it out of the ZIP with `--exclude` and list it in your
summary. Do not delete any other file without committing the deletion as `step4-deletions`.
This step writes no document of its own besides the ZIP and the JSON.""",
    5: """Read .agents/skills/prepublication-review/SKILL.md and the files it says to read, and
follow it for package {id}. If the full Metadata Editor JSON export is not in report/{id}/,
use report/{id}/{id}_merge.json, list the checks you had to skip and call the verdict provisional.
Keep the report to the template: header, the Verdict, PII and ZIP SHA-256 lines, the bullet list of changes and
at most one "Not checked" line (name the skipped check groups in that one line, e.g. "J1 fields, DataCite, tags").
Record the SHA-256 of the ZIP you reviewed in the report, as the skill describes. Unless the verdict is a
Hold, draft the final email to the authors (prepare-publication/SKILL.md, Step 7) as
report/{id}/emails/4_final_published.md, leaving the repository link as [INSERT LINK].""",
}


# Private path: the agent never sees data and never runs the code. The reviewer runs
# private_bundle.py prerun before step 1, runs the package on the secure machine, and runs
# private_bundle.py postrun before step 2.
PRIVATE_DATA = ("Private data. package/{id}/ holds only code, docs, data_hash_report_prerun.csv and "
                "variable_inventory.csv (after the run also hash_comparison.csv, code_changes.diff, "
                "system_info.txt and the outputs). Follow each skill's private-data section.")

PRIVATE_STEP2 = """Read .agents/skills/run-package/SKILL.md in full and follow its private-data section for
package {id}. Read report/{id}/completeness_check.md first. If its verdict is RETURN TO AUTHORS,
write BLOCKED_step2.md and stop. Do not run the code: the data is not here. The reviewer ran the
package twice on the secure machine and private_bundle.py postrun copied the results into
package/{id}/. If hash_comparison.csv or system_info.txt is missing, write BLOCKED_step2.md
saying the reviewer must run postrun, and stop. Otherwise write the Run Log from
hash_comparison.csv, code_changes.diff, system_info.txt and bundle_manifest_postrun.txt as
report/{id}/run_log.md, and the confirmation email draft as report/{id}/emails/2_run_confirmation.md."""


def parse_steps(text):
    out = []
    try:
        for part in text.split(","):
            if "-" in part:
                a, b = part.split("-")
                out.extend(range(int(a), int(b) + 1))
            else:
                out.append(int(part))
    except ValueError:
        out = []
    if not out or any(s not in STEPS for s in out):
        sys.exit(f"--steps {text!r}: use step numbers 1 to 5, e.g. 1-5, 2 or 3-5.")
    return out


# Steps other than the run should take minutes. Without a limit, a stalled API call can hold
# a step for hours (step 3 of RR_WLD_2026_806: 122 min). Step 2 runs the package: no limit.
DEFAULT_TIMEOUT_MIN = 60

CODE_EXT = {".do": "Stata", ".ado": "Stata", ".r": "R", ".rmd": "R", ".qmd": "R", ".py": "Python",
            ".ipynb": "Python", ".m": "Matlab", ".jl": "Julia"}
NOT_AUTHOR_CODE = {"ado", "renv", "myenv", "venv", ".venv", "site-packages", "node_modules", "__macosx", ".git"}


def resolve_id(given):
    """The full ID, or a number that exactly one folder in package/ or report/ ends with."""
    dirs = [d for d in (REPO / "package", REPO / "report") if d.is_dir()]
    if any((d / given).is_dir() for d in dirs):
        return given
    hits = sorted({p.name for d in dirs for p in d.iterdir() if p.is_dir() and p.name.endswith("_" + given)})
    if len(hits) > 1:
        sys.exit(f"{given!r} matches several packages: {', '.join(hits)}. Give the full ID.")
    return hits[0] if hits else given


def detect_software(pkg):
    """Languages of the code files in package/[ID]/ (also inside a ZIP not yet extracted)."""
    names = []
    for path in pkg.rglob("*") if pkg.is_dir() else []:
        if path.is_file():
            names.append(path.relative_to(pkg).as_posix())
            if path.suffix.lower() == ".zip":
                try:
                    import zipfile
                    with zipfile.ZipFile(path) as z:
                        names += z.namelist()
                except Exception:
                    pass
    count = {}
    for name in names:
        parts = name.lower().split("/")
        lang = CODE_EXT.get(os.path.splitext(parts[-1])[1])
        if lang and not NOT_AUTHOR_CODE.intersection(parts[:-1]):
            count[lang] = count.get(lang, 0) + 1
    return ", ".join(sorted(count, key=count.get, reverse=True))


def fill_details(args, outdir):
    """Title, reviewer, software and --private: from the command line, else from the last run
    of this package, else detected. Returns one line saying what is used and where it came from."""
    saved = ai_summary.load(outdir / "run_info.json")
    src = {}

    def pick(key, *others):
        if getattr(args, key):
            return
        for value, where in ((saved.get(key), "last run"), *others):
            if value:
                setattr(args, key, value)
                src[key] = where
                return
    git_name = subprocess.run(["git", "-C", str(REPO), "config", "user.name"],
                              capture_output=True, text=True).stdout.strip()
    pick("title")
    pick("reviewer", (os.environ.get("RRR_REVIEWER"), "RRR_REVIEWER"), (git_name, "git user.name"))
    pick("software", (detect_software(REPO / "package" / args.id), "detected"))
    if saved.get("private") and not args.private:
        args.private, src["private"] = True, "last run"
    if not args.software:
        args.software, src["software"] = "not stated: identify it from the code files", "not detected"

    def show(key):
        return f"{getattr(args, key) or f'no {key} yet'}" + (f" ({src[key]})" if key in src else "")
    return (f"{args.id} · {show('title')} · {show('software')} · {show('reviewer')}"
            + (f" · private data{' (last run)' if 'private' in src else ''}" if args.private else ""))


def me(args, *more):
    return " ".join(["python scripts/headless_review.py", args.id, *more])


def print_status(args, s):
    """Where the review stands, from the files in report/[ID]/. Runs nothing, writes nothing."""
    width = max(len(label) for _, _, label in ai_summary.SKILLS)
    for n, _, label in ai_summary.SKILLS:
        state = s["state"][n]
        mark = "done" if state == "Completed" else "--" if state == "Not run" else "!!"
        note = s["did"].get(n, "")
        if state not in ("Completed", "Not run"):
            note = (note + " | " if note else "") + state
        print(f" {n}  {label:<{width}}  {mark:<4}  {note}")
    print(f"\nStatus: {s['status']}.")
    if s["pending"]:
        print("\nFor you to check or do:")
        for item in s["pending"]:
            print(f" - {item}")
    if s["next"]:
        print(f"\nNext: {me(args, '--steps next')}    (starts at step {s['next']})")
    elif s["returned"]:
        print("\nNext: with the authors. Send emails/1_missing_items.md; run step 1 again on the resubmission.")
    elif s["not_repro"]:
        print("\nNext: with the authors. Send the report (emails/3_report_to_authors.md); start again from "
              "step 1 with the resubmission.")
    else:
        print("\nAll five steps have run. Check ai_use_summary.md and paste it into the GitHub issue.")


def prerequisites(n, args):
    """What step n needs from the steps before it. Returns (problems, hard); hard means
    no later step can run either, whatever --keep-going says."""
    rep, pkg = REPO / "report" / args.id, REPO / "package" / args.id
    need = []
    if n == 1 and not (pkg.is_dir() and any(pkg.iterdir())):
        need.append(f"package/{args.id}/ is missing or empty. Copy the submission there"
                    + (" (private path: run private_bundle.py prerun)." if args.private else "."))
    if n == 2:
        comp = ai_summary.completeness(rep)
        if not comp:
            need.append(f"report/{args.id}/completeness_check.md is missing. Run step 1 first.")
        elif comp["verdict"] == "RETURN TO AUTHORS":
            need.append("The completeness verdict is RETURN TO AUTHORS. Review and send the author "
                        "email, and run step 1 again on the resubmission.")
        if args.private:
            missing = [f for f in ("hash_comparison.csv", "system_info.txt") if not (pkg / f).is_file()]
            if missing:
                need.append(f"{', '.join(missing)} not in package/{args.id}/. Run the package on the "
                            "secure machine, then private_bundle.py postrun.")
    if n == 3 and not (rep / "run_log.md").is_file():
        need.append(f"report/{args.id}/run_log.md is missing. Run step 2 first.")
    if n == 4:
        exh = ai_summary.exhibit_counts(rep, args.id)
        if not exh or not exh["total"]:
            need.append(f"No exhibit statuses found in report/{args.id}/verification_report_{args.id}.md. Run step 3 first.")
        elif exh["counts"]["Does not reproduce"]:
            names = ", ".join(exh["names"]["Does not reproduce"])
            return [f"The package does not reproduce ({names}), so it is not prepared for publication. "
                    "Check the report, send it to the authors, and start again from step 1 with the resubmission."], True
        if not (rep / f"reproducibility_report_{args.id}.pdf").is_file():
            need.append(f"report/{args.id}/reproducibility_report_{args.id}.pdf is missing. Export it (step 3).")
    if n == 5:
        if not (rep / f"{args.id}.zip").is_file():
            need.append(f"report/{args.id}/{args.id}.zip is missing. Run step 4 first.")
        if not ((rep / f"{args.id}.json").is_file() or (rep / f"{args.id}_merge.json").is_file()):
            need.append(f"Neither {args.id}.json (Metadata Editor export) nor {args.id}_merge.json is in report/{args.id}/.")
    return need, False


def archive_attempt(outdir, n, skill):
    """Keep what an earlier attempt at this step left, under a time-stamped name."""
    stamp = f"{datetime.now():%Y-%m-%d_%H%M%S}"
    blocked = outdir / f"BLOCKED_step{n}.md"
    if blocked.exists():
        blocked.rename(outdir / f"BLOCKED_step{n}_resolved_{stamp}.md")
    for ext in ("jsonl", "md"):
        old = outdir / f"step{n}_{skill}.{ext}"
        if old.exists():
            old.rename(outdir / f"step{n}_{skill}.before_{stamp}.{ext}")


def block(outdir, n, problems):
    (outdir / f"BLOCKED_step{n}.md").write_text(
        f"# Step {n} did not run\n\n" + "\n".join(f"- {p}" for p in problems)
        + "\n\nWritten by headless_review.py; no AI session was started for this step.\n", encoding="utf-8")
    for p in problems:
        print(f"   ! {p}")


def track(args, *cmd):
    """Run track_package.py for this package; returns its output."""
    res = subprocess.run([sys.executable, str(TRACK), cmd[0], "--id", args.id, "--root", str(REPO), *cmd[1:]],
                         capture_output=True, text=True)
    return res.returncode, (res.stdout + res.stderr).strip()


def tracked(args):
    return (REPO / "report" / args.id / "evidence" / "package.git").is_dir()


def check_package_repo(args, n, outdir):
    """After a step: the package repo must have no remote, and nothing may be left
    uncommitted. Returns False if the run must stop."""
    pkg = REPO / "package" / args.id
    if not tracked(args):
        return True

    def git(*a):
        return subprocess.run(["git", "-C", str(pkg), *a], capture_output=True, text=True).stdout.strip()
    if git("remote"):
        block(outdir, n, [f"The Git repo of package/{args.id}/ has a remote ({git('remote')}). It must stay local. "
                          "Check `git remote -v`, remove it, and check nothing was pushed."])
        return False
    if git("status", "--porcelain"):
        code, out = track(args, "commit", "--label", f"step{n}-uncommitted",
                          "--note", "Left uncommitted by the agent; committed by headless_review.py.")
        print(f"   ! The agent left changes uncommitted in package/{args.id}/. Committed as step{n}-uncommitted.")
        zc = ai_summary.load(REPO / "report" / args.id / "evidence" / "zip_check.json")
        if n == 4 and zc:  # the ZIP no longer matches the last commit: build it again, same exclusions
            extra = [x for e in zc.get("excluded", []) for x in ("--exclude", e.rstrip("/"))]
            code, out = track(args, "zip", "--allow-missing", *extra)
            print("   " + out.replace("\n", "\n   "))
    return True


def run_step(n, args, outdir):
    skill, label = STEPS[n]
    ctx = dict(id=args.id, title=args.title, software=args.software, reviewer=args.reviewer,
               data=args.data, n=n, date=f"{datetime.now():%Y-%m-%d}")
    task = PRIVATE_STEP2 if (args.private and n == 2) else STEP_TASKS[n]
    prompt = task.format(**ctx) + "\n" + HEADLESS_RULES.format(**ctx)
    transcript = outdir / f"step{n}_{skill}.jsonl"
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--strict-mcp-config", "--permission-mode", PERMISSION_MODE,
           "--allowedTools", *ALLOWED, "--disallowedTools", *DISALLOWED]
    if args.model:
        cmd += ["--model", args.model]
    if args.max_budget:
        cmd += ["--max-budget-usd", str(args.max_budget)]

    started = datetime.now()
    start = time.time()
    result, timed_out = None, []
    with open(transcript, "w", encoding="utf-8") as log:
        env = {**os.environ, "CLAUDE_CODE_PROMPT_CACHE_TTL": CACHE_TTL}
        proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8")
        timer = None
        limit = args.timeout_min
        if limit is None:  # not set: only the step that runs the package's code has no limit
            limit = None if (n == 2 and not args.private) else DEFAULT_TIMEOUT_MIN
        if limit:
            timer = threading.Timer(limit * 60, lambda: (timed_out.append(1), proc.kill()))
            timer.start()
        try:
            for line in proc.stdout:
                log.write(line)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "assistant":
                    for block_ in msg.get("message", {}).get("content", []):
                        if block_.get("type") == "tool_use":
                            desc = block_.get("input", {}).get("description") or block_.get("input", {}).get("file_path") or ""
                            print(f"   · {block_['name']} {str(desc)[:90]}", flush=True)
                elif msg.get("type") == "result":
                    result = msg
            proc.wait()
        except KeyboardInterrupt:
            proc.kill()
            raise
        finally:
            if timer:
                timer.cancel()
    elapsed = time.time() - start

    row = {"step": n, "skill": skill, "started": f"{started:%Y-%m-%d %H:%M}", "turns": 0,
           "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0,
           "total_tokens": 0, "cost_usd": 0, "minutes": round(elapsed / 60, 1), "denied_tools": 0, "model": args.model or ""}
    if result is None:
        row["status"] = f"timeout after {limit:g} min" if timed_out else f"no result (exit {proc.returncode})"
        print(f"   ! {row['status']}. See {transcript.name}")
        return row

    (outdir / f"step{n}_{skill}.md").write_text(result.get("result") or "", encoding="utf-8")

    inp = out = cread = cwrite = 0
    models = []
    for model, u in (result.get("modelUsage") or {}).items():
        models.append(model)
        inp += u.get("inputTokens", 0)
        out += u.get("outputTokens", 0)
        cread += u.get("cacheReadInputTokens", 0)
        cwrite += u.get("cacheCreationInputTokens", 0)
    row.update({
        # an errored session can still say subtype "success"; terminal_reason says why it ended
        "status": "ok" if not result.get("is_error") else
                  "error: " + str(result.get("terminal_reason") or result.get("subtype") or "unknown"),
        "turns": result.get("num_turns", 0),
        "input_tokens": inp, "output_tokens": out,
        "cache_read_tokens": cread, "cache_write_tokens": cwrite,
        "total_tokens": inp + out + cread + cwrite,
        "cost_usd": round(result.get("total_cost_usd") or 0, 4),
        "denied_tools": len(result.get("permission_denials") or []),
        "model": ", ".join(models),
    })
    print(f"   {row['status']} · {row['turns']} turns · {row['total_tokens']:,} tokens "
          f"({row['output_tokens']:,} output) · ${row['cost_usd']} · {row['minutes']} min", flush=True)
    for d in result.get("permission_denials") or []:
        print(f"   ! denied: {d.get('tool_name')} {str(d.get('tool_input', ''))[:100]}")
    return row


def write_usage(outdir, row):
    """Add this attempt to token_usage.csv (which keeps every attempt) and rewrite
    token_usage.md (latest attempt of each step)."""
    fields = ["step", "skill", "attempt", "started", "status", "turns", "input_tokens", "output_tokens",
              "cache_read_tokens", "cache_write_tokens", "total_tokens", "cost_usd",
              "minutes", "denied_tools", "model"]
    path_csv = outdir / "token_usage.csv"
    allrows = []
    if path_csv.exists():
        with open(path_csv, newline="", encoding="utf-8") as f:
            allrows = list(csv.DictReader(f))
    row["attempt"] = 1 + sum(int(r["step"]) == row["step"] for r in allrows)
    allrows.append(row)
    with open(path_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(allrows)

    def num(r, k):
        return float(r.get(k) or 0)
    latest = {int(r["step"]): r for r in allrows}
    latest = [latest[k] for k in sorted(latest)]
    earlier = sum(num(r, "cost_usd") for r in allrows) - sum(num(r, "cost_usd") for r in latest)
    lines = ["# Token usage", "",
             "| Step | Skill | Status | Turns | Total tokens | Output | Cache read | Cost (USD) | Minutes |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in latest:
        lines.append(f"| {r['step']} | {r['skill']} | {r.get('status') or 'ok'} | {int(num(r,'turns'))} | {int(num(r,'total_tokens')):,} | "
                     f"{int(num(r,'output_tokens')):,} | {int(num(r,'cache_read_tokens')):,} | "
                     f"{num(r,'cost_usd'):.2f} | {num(r,'minutes'):.1f} |")
    lines.append(f"| **All** | | | {int(sum(num(r,'turns') for r in latest))} | "
                 f"**{int(sum(num(r,'total_tokens') for r in latest)):,}** | "
                 f"{int(sum(num(r,'output_tokens') for r in latest)):,} | "
                 f"{int(sum(num(r,'cache_read_tokens') for r in latest)):,} | "
                 f"**{sum(num(r,'cost_usd') for r in latest):.2f}** | "
                 f"{sum(num(r,'minutes') for r in latest):.1f} |")
    lines += ["", "Total tokens = input + output + cache read + cache write. Cache reads are most "
              "of the tokens but not of the cost: the agent re-reads its context on every turn, at "
              "a tenth of the input price. Cache writes and output cost more per token. "
              "Cost is Claude Code's estimate at list price."]
    if earlier:
        lines += ["", f"The table shows the latest attempt of each step. Earlier attempts cost a further "
                  f"${earlier:.2f}; every attempt is in token_usage.csv."]
    (outdir / "token_usage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Run the review skills headless, one session per skill.")
    ap.add_argument("package", nargs="?", metavar="ID",
                    help="Package ID, or just its number when one folder in package/ ends with it (e.g. 806)")
    ap.add_argument("--id", help="Same as the positional ID")
    ap.add_argument("--title", help="Paper title. Needed on the first run only; remembered after that")
    ap.add_argument("--software", help="Default: remembered, else detected from the code files")
    ap.add_argument("--reviewer", help="Default: remembered, else RRR_REVIEWER, else git config user.name")
    ap.add_argument("--status", action="store_true",
                    help="Show where the review stands and what to do next. Runs nothing")
    ap.add_argument("--private", action="store_true",
                    help="Private path: work from the bundle that private_bundle.py built; never run the code")
    ap.add_argument("--data", help="One line on the data (default depends on --private)")
    ap.add_argument("--steps", default="1-5", help="e.g. 1-5, 2, 3-5, or next (from the first unfinished step)")
    ap.add_argument("--model", help="e.g. claude-sonnet-5-5 (default: your Claude Code default)")
    ap.add_argument("--max-budget", type=float, help="Stop a step if it would spend more than this (USD)")
    ap.add_argument("--timeout-min", type=float,
                    help="Stop a step after this many minutes; 0 = no limit (default: 60, and no limit "
                         "for step 2 when it runs the code)")
    ap.add_argument("--keep-going", action="store_true",
                    help="Continue after a step the agent blocked or that failed (never past a package that does not reproduce)")
    args = ap.parse_args()
    if not (args.id or args.package):
        ap.error("give the package ID, e.g. headless_review.py RR_WLD_2026_806 (or just 806)")
    args.id = resolve_id(args.id or args.package)
    outdir = REPO / "report" / args.id / "headless"
    if not any((REPO / d / args.id).is_dir() for d in ("package", "report")):
        sys.exit(f"No package/{args.id}/ folder. Copy the submission into package/[PACKAGE_ID]/ first"
                 " (private data: run private_bundle.py prerun).")
    print(fill_details(args, outdir), flush=True)

    if args.status or args.steps == "next":
        state = ai_summary.collect(args.id, REPO, args.title, args.reviewer, with_usage=False)
        if args.status or not state["next"]:
            print()
            print_status(args, state)
            return 0
        args.steps = f"{state['next']}-5" if state["next"] < 5 else "5"
        print(f"Resuming at step {state['next']}.")
    if not args.title:
        sys.exit(f"First run of {args.id}: add --title \"Paper title\". It is remembered after that.")
    if not args.reviewer:
        sys.exit("No reviewer name found. Add --reviewer \"Your name\" (remembered after that), "
                 "or set RRR_REVIEWER.")
    if not args.data:
        args.data = PRIVATE_DATA.format(id=args.id) if args.private else "All data is in the package (public path)."
    steps = parse_steps(args.steps)

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "run_info.json").write_text(json.dumps({
        "id": args.id, "title": args.title, "reviewer": args.reviewer, "software": args.software,
        "private": args.private, "steps": args.steps, "date": f"{datetime.now():%Y-%m-%d}"}, indent=2), encoding="utf-8")

    failed = False
    for n in steps:
        skill, label = STEPS[n]
        print(f"\n== {label} ==  ({datetime.now():%H:%M:%S})", flush=True)
        archive_attempt(outdir, n, skill)
        problems, hard = prerequisites(n, args)
        if problems:
            block(outdir, n, problems)
        else:
            if n == 4 and not tracked(args):
                # No history from step 2 (private path, or a step 2 from before tracking existed)
                code, out = track(args, "init", "--label", "postrun-bundle" if args.private else "step4-start")
                print("   " + out.replace("\n", "\n   "))
            row = run_step(n, args, outdir)
            write_usage(outdir, row)
            hard = not check_package_repo(args, n, outdir)
            if row["status"] != "ok" and not (outdir / f"BLOCKED_step{n}.md").exists():
                print(f"   ! Step {n} did not finish: {row['status']}.")
                failed = True
                if not args.keep_going:
                    break
        if (outdir / f"BLOCKED_step{n}.md").exists():
            failed = True
            print(f"\nStopped: step {n} is blocked. See report/{args.id}/headless/BLOCKED_step{n}.md")
            if hard or not args.keep_going:
                break

    if tracked(args):
        code, out = track(args, "changes")
        print("\n" + out)
    summary, pending = ai_summary.build(args.id, REPO, args.title, args.reviewer, "headless")
    print(f"\nToken usage: report/{args.id}/headless/token_usage.md")
    print(f"AI use summary ({len(pending)} pending item(s)): report/{args.id}/ai_use_summary.md"
          "  <- check it, fill it in and paste it into the GitHub issue")
    for p in pending:
        print(f"   - {p}")
    if failed:
        print(f"\nAfter fixing the cause: {me(args, '--steps next')}")
    print(f"Where it stands, any time: {me(args, '--status')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
