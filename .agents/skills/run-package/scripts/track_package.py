#!/usr/bin/env python3
"""
Package change tracking
-----------------------
Keeps the record a reviewer needs to check what the AI changed in a package and whether
the code really ran. The package stays in package/[ID]/; everything else goes to
report/[ID]/evidence/, including the Git history (package.git), so the package folder
never holds a .git folder and nothing has to be deleted before zipping.

    S=.agents/skills/run-package/scripts/track_package.py
    python $S init    --id ID --raw-data Data/Raw        # local Git, commit "initial-package"
    python $S run     --id ID --n 1 --log main.log -- stata-mp -b do main.do
    python $S commit  --id ID --label fix-root-path --note "main.do line 12: root path"
    python $S run     --id ID --n 2 --log main.log -- stata-mp -b do main.do
    python $S compare --id ID                            # run 1 vs run 2, by SHA-256
    python $S commit  --id ID --label step4-license      # one commit per step 4 action
    python $S zip     --id ID --exclude "Reproducibility package/Data/Restricted"
    python $S changes --id ID                            # writes AI_CHANGES.md

Written to report/[ID]/evidence/:
    package.git/          Git history of package/[ID]/ (local only, never pushed or shipped)
    run_times.csv         every run: command, start, end, seconds, exit code (measured here)
    runN_stdout.log       what the main script printed; runN_<name>.log = copy of its own log
    runN_hashes.csv       SHA-256, size and modification time of every file after run N,
                          including the binary files Git ignores (.dta, .xlsx, .pdf)
    run_comparison.csv    run 1 vs run 2
    AI_CHANGES.md         every change since initial-package, with commit and file:line
    zip_manifest.csv      every file in the ZIP with its SHA-256, checked against the last commit
    zip_check.json        ZIP SHA-256 and the result of that check

To look at the history yourself: `git -C package/[ID] log --oneline` and
`git -C package/[ID] diff initial-package..HEAD`. Commits made here are authored
"RRR review agent (AI)". Standard library only.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[4]  # .agents/skills/run-package/scripts -> repo root
AI_AUTHOR = ["-c", "user.name=RRR review agent (AI)", "-c", "user.email=ai-agent@localhost"]

GITIGNORE_MARK = "## This .gitignore is for reproducibility packages to track changes in outputs only"
GITIGNORE = GITIGNORE_MARK + """

## Binary output files - Git cannot show meaningful diffs for these
*.pdf
*.xlsx
*.xls
*.dta
*.zip
*.docx
*.doc
*.stswp
*.rar
*.7z
*.rds
*.RData
*.sav
*.parquet
*.feather
*.pkl

## Stata, R, Python and system files
*.smcl
.Rhistory
__pycache__/
*.pyc
myenv/
.DS_Store
Thumbs.db
~$*

## Ignore the raw data folder
"""

CODE_EXT = {".do", ".ado", ".r", ".rmd", ".qmd", ".py", ".ipynb", ".jl", ".m", ".sh", ".bat",
            ".ps1", ".sps", ".sas", ".mata"}
# A script that writes tables or figures: a change to it can change an exhibit.
WRITES_OUTPUT = re.compile(
    r"esttab|estout|outreg2|outsheet|export\s+(delimited|excel)|putexcel|putdocx|graph\s+(export|save)|"
    r"texsave|collect\s+export|ggsave|write[._](csv|table|xlsx|dta)|fwrite|stargazer|modelsummary|"
    r"etable|kable|\bpng\(|\bpdf\(|savefig|to_(csv|latex|excel|stata)|writetable|saveas", re.I)
RUN_LABEL = re.compile(r"^(first-run|second-run|run-\d+)")
SKIP_DIRS = {".git", "__pycache__", "myenv", ".venv", "venv", "node_modules", "__MACOSX"}
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini", ".Rhistory"}  # system files: not evidence
NEVER_ZIP = {".git", ".gitignore", ".gitattributes", ".DS_Store", "Thumbs.db", "desktop.ini",
             ".Rhistory", "__MACOSX", "__pycache__"}
ZIP_FOLDER = "Reproducibility package"


def paths(a):
    root = Path(a.root).resolve()
    pkg, rep = root / "package" / a.id, root / "report" / a.id
    if not pkg.is_dir():
        sys.exit(f"ERROR: package folder not found: {pkg}")
    ev = rep / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    return pkg, rep, ev


def git(pkg, *args, check=True):
    res = subprocess.run(["git", "-C", str(pkg), "-c", "core.quotepath=off", *args],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        sys.exit(f"ERROR: git {' '.join(args[:3])} failed: {res.stderr.strip()[-400:]}")
    return res.stdout


def has_commits(pkg):
    return bool(git(pkg, "rev-parse", "--verify", "-q", "HEAD", check=False).strip())


def require_repo(pkg, ev):
    if not (ev / "package.git").is_dir() or not has_commits(pkg):
        sys.exit("ERROR: this package is not tracked yet. Run `track_package.py init` first.")
    if git(pkg, "remote").strip():
        sys.exit("ERROR: the package repository has a remote. It must stay local: remove it "
                 "(`git remote remove <name>`) and tell the reviewer.")


def commit(pkg, label, note=None, allow_empty=False):
    git(pkg, "add", "-A")
    if not allow_empty and not git(pkg, "status", "--porcelain").strip():
        return None
    msg = ["-m", label] + (["-m", note] if note else [])
    git(pkg, *AI_AUTHOR, "commit", "-q", "--allow-empty", *msg)
    return git(pkg, "rev-parse", "--short", "HEAD").strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_files(pkg):
    """Every file in the package except Git, virtual environments and the renv library."""
    for dirpath, dirnames, filenames in os.walk(pkg):
        here = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS
                             and not (d == "library" and here.name == "renv"))
        for fn in sorted(filenames):
            p = here / fn
            if fn != ".git" and fn not in JUNK and p.is_file() and not p.is_symlink():
                yield p


def tracked_files(pkg):
    return set(git(pkg, "ls-files", "-z").split("\0")) - {""}


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if Path(r.get("file") or "x").name not in JUNK]


# ── init ────────────────────────────────────────────────────────────────────────────────

def cmd_init(a):
    pkg, rep, ev = paths(a)
    gitdir = ev / "package.git"

    # A Git repo inside a subfolder (the authors' own, or one from an earlier review) would
    # hide that subfolder's files from this one. Move it out; it is kept as evidence.
    for dirpath, dirnames, _ in os.walk(pkg):
        if Path(dirpath) != pkg and ".git" in dirnames:
            src = Path(dirpath) / ".git"
            dst = ev / "nested_git" / Path(dirpath).relative_to(pkg).as_posix().replace("/", "__")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            dirnames.remove(".git")
            print(f"  Moved a nested Git repo out of the package: {src.relative_to(pkg)} -> {dst.relative_to(rep)}")

    if gitdir.is_dir() and has_commits(pkg):
        print(f"Already tracked ({gitdir.relative_to(rep.parent.parent)}). History so far:")
        print(git(pkg, "log", "--oneline", "--reverse"))
        return 0

    # --separate-git-dir keeps the history in report/[ID]/evidence/ and leaves only a small
    # pointer file (.git) in the package. An existing .git folder at the package root is moved.
    res = subprocess.run(["git", "init", "-q", "--separate-git-dir", str(gitdir), str(pkg)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ERROR: git init failed: {res.stderr.strip()}")
    if git(pkg, "remote").strip():
        sys.exit("ERROR: the package already had a Git repo with a remote. Remove the remote first.")

    ignore = pkg / ".gitignore"
    old = ignore.read_text(encoding="utf-8", errors="replace") if ignore.exists() else ""
    if GITIGNORE_MARK not in old:
        # **/ so the rule still holds after step 4 moves the folder into "Reproducibility package/"
        raw = "".join(f"**/{d.strip('/')}/\n" for d in (a.raw_data or ["raw_data"]))
        ignore.write_text((old.rstrip() + "\n\n" if old.strip() else "") + GITIGNORE + raw, encoding="utf-8")

    print(f"Tracking package/{a.id}/ (history in report/{a.id}/evidence/package.git)")
    if has_commits(pkg) and not a.label:
        # A repo from before this helper: keep its commits and add nothing on top.
        print("  Kept the existing history:")
        print(git(pkg, "log", "--oneline", "--reverse"))
        return 0
    label = a.label or "initial-package"
    short = commit(pkg, label, allow_empty=True)
    files = tracked_files(pkg)
    size = sum((pkg / f).stat().st_size for f in files if (pkg / f).is_file())
    print(f"  Commit {short} \"{label}\": {len(files)} tracked file(s), {size / 1e6:.1f} MB")
    if size > 200e6:
        print("  ! More than 200 MB is tracked. If that is raw data, add its folder to .gitignore "
              "(--raw-data) so the data is not saved twice.")
    return 0


# ── run ─────────────────────────────────────────────────────────────────────────────────

def manifest(pkg, since=None):
    rows = []
    for p in walk_files(pkg):
        st = p.stat()
        rows.append({"file": p.relative_to(pkg).as_posix(), "size_bytes": st.st_size,
                     "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                     "sha256": sha256(p),
                     "written_in_run": "" if since is None else ("yes" if st.st_mtime >= since else "no")})
    return rows


MANIFEST_FIELDS = ["file", "size_bytes", "modified", "sha256", "written_in_run"]


def cmd_run(a):
    pkg, rep, ev = paths(a)
    require_repo(pkg, ev)
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        sys.exit("ERROR: give the command after --, e.g. -- Rscript main.R")
    cwd = pkg / a.cwd if a.cwd else pkg
    out_log = ev / f"run{a.n}_stdout.log"

    start = datetime.now().astimezone()
    t0 = time.time()
    try:
        with open(out_log, "w", encoding="utf-8") as log:
            code = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL).returncode
    except FileNotFoundError:
        sys.exit(f"ERROR: command not found: {cmd[0]}")
    seconds = time.time() - t0
    end = datetime.now().astimezone()

    # Stata in batch mode exits 0 even when the do-file stops on an error; its log says r(NNN);
    result = "ok" if code == 0 else "failed"
    for lg in a.log or []:
        src = cwd / lg if (cwd / lg).exists() else pkg / lg
        if not src.exists():
            print(f"  ! Log not found: {lg}")
            continue
        shutil.copy2(src, ev / f"run{a.n}_{src.name}")
        if re.search(r"^r\(\d+\);\s*$", src.read_text(encoding="utf-8", errors="replace"), re.M):
            result = "failed"
            print(f"  ! {src.name} ends with a Stata error code")

    short = ""
    if result == "ok":
        rows = manifest(pkg, since=int(t0))
        write_csv(ev / f"run{a.n}_hashes.csv", MANIFEST_FIELDS, rows)
        base = {1: "first-run", 2: "second-run"}.get(a.n, f"run-{a.n}")
        again = sum(1 for s in git(pkg, "log", "--format=%s").splitlines() if s.startswith(base))
        label = base if not again else f"{base} (rerun {again})"
        short = commit(pkg, label, note=f"{' '.join(cmd)}\n{seconds:.1f} seconds", allow_empty=True)

    times = ev / "run_times.csv"
    fields = ["run", "result", "seconds", "start", "end", "exit_code", "command", "cwd", "commit"]
    old = read_csv(times)
    write_csv(times, fields, old + [{
        "run": a.n, "result": result, "seconds": f"{seconds:.1f}",
        "start": start.isoformat(timespec="seconds"), "end": end.isoformat(timespec="seconds"),
        "exit_code": code, "command": " ".join(cmd),
        "cwd": cwd.relative_to(pkg).as_posix() if cwd != pkg else ".", "commit": short}])

    tail = out_log.read_text(encoding="utf-8", errors="replace").splitlines()
    if result == "ok":
        written = sum(1 for r in rows if r["written_in_run"] == "yes")
        print(f"Run {a.n}: ok in {seconds:.1f} s ({start:%H:%M:%S} to {end:%H:%M:%S}), "
              f"{written} file(s) written, commit {short} \"{label}\"")
        print("\n".join("  | " + line for line in tail[-8:]))
        return 0
    print(f"Run {a.n}: FAILED after {seconds:.1f} s (exit code {code}). Nothing was committed.")
    print("\n".join("  | " + line for line in tail[-40:]))
    print("Fix the cause, commit the fix on its own (`commit --label fix-...`), then run again.")
    return 1


def cmd_compare(a):
    pkg, rep, ev = paths(a)
    first = {r["file"]: r for r in read_csv(ev / f"run{a.a}_hashes.csv")}
    second = {r["file"]: r for r in read_csv(ev / f"run{a.b}_hashes.csv")}
    if not first or not second:
        sys.exit(f"ERROR: run{a.a}_hashes.csv or run{a.b}_hashes.csv is missing. Run both runs first.")
    tracked = tracked_files(pkg)
    rows = []
    for f in sorted(set(first) | set(second)):
        r1, r2 = first.get(f), second.get(f)
        if r1 and r2:
            if r1["sha256"] == r2["sha256"] and "yes" not in (r1["written_in_run"], r2["written_in_run"]):
                continue  # an input neither run touched
            status = "identical" if r1["sha256"] == r2["sha256"] else "different"
        else:
            status = f"only in run {a.a if r1 else a.b}"
        rows.append({"file": f, "status": status, "tracked_by_git": "yes" if f in tracked else "no",
                     f"sha256_run{a.a}": r1["sha256"] if r1 else "", f"sha256_run{a.b}": r2["sha256"] if r2 else ""})
    write_csv(ev / "run_comparison.csv",
              ["file", "status", "tracked_by_git", f"sha256_run{a.a}", f"sha256_run{a.b}"], rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"Run {a.a} vs run {a.b}: " + (", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "no files written")
          + " -> evidence/run_comparison.csv")
    for r in [r for r in rows if r["status"] != "identical"][:30]:
        print(f"  {r['status']}: {r['file']}" + ("" if r["tracked_by_git"] == "yes" else "  (binary: may be a timestamp only)"))
    return 0


def cmd_commit(a):
    pkg, rep, ev = paths(a)
    require_repo(pkg, ev)
    short = commit(pkg, a.label, a.note)
    if not short:
        print(f"Nothing to commit for \"{a.label}\": no tracked file changed.")
        return 0
    print(f"Commit {short} \"{a.label}\"")
    print(git(pkg, "show", "--stat", "--format=", "HEAD").rstrip()[-1500:])
    return 0


# ── changes ─────────────────────────────────────────────────────────────────────────────

def hunks(pkg, parent, sha, paths):
    """file:line and the lines removed/added, from a zero-context diff."""
    out, cur = [], None
    for line in git(pkg, "diff", "-U0", "-M", "--no-color", parent, sha, "--", *paths, check=False).splitlines():
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            line_no = int(m.group(3)) if m.group(4) != "0" else int(m.group(1))
            cur = {"line": line_no, "old": [], "new": []}
            out.append(cur)
        elif cur is not None and line[:1] in "+-" and not line.startswith(("+++", "---")):
            cur["old" if line[0] == "-" else "new"].append(line[1:].strip()[:160])
    return out


def cmd_changes(a):
    pkg, rep, ev = paths(a)
    require_repo(pkg, ev)
    log = git(pkg, "log", "--reverse", "--format=%H%x1f%h%x1f%ad%x1f%an%x1f%s%x1f%b%x1e", "--date=format:%Y-%m-%d %H:%M")
    commits = [dict(zip(["sha", "short", "date", "author", "label", "note"], c.strip("\n").split("\x1f")))
               for c in log.split("\x1e") if c.strip()]
    for c, parent in zip(commits[1:], commits):
        c["parent"] = parent["sha"]
        c["files"] = [ln.split("\t") for ln in
                      git(pkg, "diff", "--name-status", "-M", parent["sha"], c["sha"]).splitlines() if ln]
    commits[0]["files"] = []
    run_outputs = set()  # files the runs wrote, followed through later renames
    for c in commits:
        for f in c["files"]:
            if RUN_LABEL.match(c["label"]) or (f[0][0] == "R" and f[1] in run_outputs):
                run_outputs.add(f[-1])

    L = [f"# AI changes to the package: {a.id}", "",
         f"Generated {datetime.now():%Y-%m-%d %H:%M} from the local Git history of `package/{a.id}/` "
         f"(kept in `report/{a.id}/evidence/package.git`, never pushed or shipped). It lists every "
         "tracked file added, edited or removed since the first commit. Nothing here has been "
         "checked by a person yet.", "",
         "Check any line yourself:", "", "```bash",
         f"git -C package/{a.id} log --oneline",
         f"git -C package/{a.id} diff {commits[0]['label'].split()[0]}..HEAD --stat",
         f"git -C package/{a.id} show <commit> -- \"<file>\"", "```", "",
         "## Commits", "", "| Commit | Label | When | By | Files |", "|---|---|---|---|---:|"]
    for c in commits:
        L.append(f"| `{c['short']}` | {c['label']} | {c['date']} | {c['author']} | {len(c['files']) or '–'} |")

    code_changes, flagged, other = [], 0, []
    for c in commits[1:]:
        is_run = bool(RUN_LABEL.match(c["label"]))
        for f in c["files"]:
            status, path = f[0][0], f[-1]
            if Path(path).suffix.lower() in CODE_EXT:
                src = git(pkg, "show", f"{c['sha'] if status != 'D' else c['parent']}:{path}", check=False)
                why = []
                if f[0] == "R100":  # moved, content unchanged
                    code_changes.append((c, "moved", f, [], why))
                    continue
                if WRITES_OUTPUT.search(src):
                    why.append("this script writes tables or figures")
                if is_run:
                    why.append("changed inside a run commit, with no commit of its own")
                code_changes.append((c, status, f, hunks(pkg, c["parent"], c["sha"], f[1:]), why))
            elif not is_run:
                moved = f[0] == "R100"
                why = "an output of the run was changed outside a run" if path in run_outputs and status != "A" and not moved else ""
                other.append((c, "moved" if moved else status, f, why))

    L += ["", "## Code changes", ""]
    if not code_changes:
        L.append("No code file was added, edited or removed.")
    word = {"A": "added", "M": "edited", "D": "removed", "R": "renamed and edited", "moved": "moved, content unchanged,"}
    for c, status, f, hk, why in code_changes:
        path = f[-1]
        flag = f" ⚠️ **Check the exhibits: {'; '.join(why)}.**" if why else ""
        flagged += bool(why)
        was = f" (was `{f[1]}`)" if len(f) == 3 else ""
        L.append(f"- `{path}`{was}: {word.get(status, status)} in commit `{c['short']}` ({c['label']}).{flag}")
        if c["note"].strip() and not RUN_LABEL.match(c["label"]):
            L.append(f"  - Reason given by the AI: {' '.join(c['note'].split())}")
        if status in "MR":
            for h in hk[:20]:
                L.append(f"  - `{path}:{h['line']}`")
                L += [f"    - before: `{x}`" for x in h["old"][:4]] + [f"    - after: `{x}`" for x in h["new"][:4]]
                if len(h["old"]) > 4 or len(h["new"]) > 4:
                    L.append("    - (more lines: see `git show`)")
            if len(hk) > 20:
                L.append(f"  - {len(hk) - 20} more place(s): see `git show`")
        L.append(f"  - Check: `git -C package/{a.id} show {c['short']} -- \"{path}\"`")

    L += ["", "## Other tracked files changed outside the runs", ""]
    if not other:
        L.append("None.")
    by_commit = {}
    for c, status, f, why in other:
        by_commit.setdefault(c["short"], (c, []))[1].append((status, f, why))
    for short, (c, items) in by_commit.items():
        L.append(f"- Commit `{short}` ({c['label']}):" + (f" {' '.join(c['note'].split())}" if c["note"].strip() else ""))
        moved = [i for i in items if i[0] == "moved"]
        if len(moved) > 3:  # a folder move: one line, not one per file
            items = [i for i in items if i[0] != "moved"]
            L.append(f"  - {len(moved)} file(s) moved, content unchanged (e.g. `{moved[0][1][1]}` -> `{moved[0][1][-1]}`)")
        for status, f, why in items[:40]:
            was = f" (was `{f[1]}`)" if len(f) == 3 else ""
            L.append(f"  - {word.get(status, status).rstrip(',')}: `{f[-1]}`{was}" + (f" ⚠️ **{why}**" if why else ""))
            flagged += bool(why)
        if len(items) > 40:
            L.append(f"  - and {len(items) - 40} more: `git -C package/{a.id} show --stat {short}`")
    n_run_files = sum(len(c["files"]) for c in commits[1:] if RUN_LABEL.match(c["label"]))
    L += ["", f"The run commits changed {n_run_files} tracked file(s) in total (outputs and logs "
          "written by the code). See `run_comparison.csv` for run 1 vs run 2."]

    # Files Git ignores (.dta, .xlsx, .pdf, raw data): compare with the last run's manifest by
    # content, so a file that only moved (e.g. into "Reproducibility package/") is not reported.
    runs = sorted(ev.glob("run*_hashes.csv"), key=lambda p: int(re.search(r"run(\d+)_", p.name).group(1)))
    new, gone = [], []
    L += ["", "## Files Git does not track (binary outputs and data)", ""]
    if runs:
        last = read_csv(runs[-1])
        tracked = tracked_files(pkg)
        ever = set(git(pkg, "log", "--name-only", "--format=").splitlines())  # in Git: listed above
        now = {p.relative_to(pkg).as_posix(): sha256(p) for p in walk_files(pkg)
               if p.relative_to(pkg).as_posix() not in tracked and p.name not in NEVER_ZIP}
        before = {r["sha256"] for r in last}
        new = sorted(f for f, h in now.items() if h not in before)
        still = set(now.values()) | {sha256(pkg / f) for f in tracked if (pkg / f).is_file()}
        gone = sorted(r["file"] for r in last if r["sha256"] not in still and r["file"] not in ever)
        L.append(f"Compared with `{runs[-1].name}` (SHA-256 of every file after the last run).")
        L += ["", f"- Added or changed since the last run ({len(new)}):"] + [f"  - `{f}`" for f in new[:60]]
        L += [f"- In the last run but no longer in the package with the same content ({len(gone)}):"] \
            + [f"  - `{f}`" for f in gone[:60]]
        if gone:
            flagged += 1
            L.append("  - ⚠️ **Check each one: a removed or changed binary output or data file cannot be "
                     "seen in `git diff`.**")
    else:
        L.append("No run manifest (`runN_hashes.csv`) exists, so these files could not be checked.")

    private = {}
    if (pkg / "code_changes.diff").exists():
        diff = (pkg / "code_changes.diff").read_text(encoding="utf-8", errors="replace")
        files = re.findall(r"^diff --git a/(.+?) b/", diff, re.M)
        counts = {}
        for r in read_csv(pkg / "hash_comparison.csv"):
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        private = {"diff_files": len(files), "hash_comparison": counts}
        L += ["", "## Private-data run (done by the reviewer on the secure machine)", "",
              "The AI did not run the code. The changes made for the run are in "
              f"`package/{a.id}/code_changes.diff` ({len(files)} file(s)), written by "
              "`private_bundle.py postrun`, and the input/generated status of every data file is in "
              "`hash_comparison.csv` (" + (", ".join(f"{v} {k}" for k, v in counts.items()) or "not found") + ")."]
        L += [f"- `{f}`" for f in files[:40]]

    n_code = sum(1 for x in code_changes if x[1] != "moved")
    (ev / "AI_CHANGES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    info = {"generated": datetime.now().isoformat(timespec="seconds"), "head": commits[-1]["short"],
            "commits": [c["label"] for c in commits], "code_changes": n_code,
            "other_changes": len(other), "flagged": flagged, "untracked_new": len(new),
            "untracked_gone": len(gone), "private": private}
    (ev / "ai_changes.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"AI_CHANGES.md: {len(commits)} commit(s), {n_code} code change(s), "
          f"{len(other)} other file change(s), {flagged} flagged -> report/{a.id}/evidence/AI_CHANGES.md")
    return 0


# ── zip ─────────────────────────────────────────────────────────────────────────────────

def git_blob_id(path):
    h = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_zip(a):
    pkg, rep, ev = paths(a)
    require_repo(pkg, ev)
    dirty = git(pkg, "status", "--porcelain").strip()
    if dirty:
        sys.exit("ERROR: there are uncommitted changes, so the ZIP would not match the last commit. "
                 "Commit them first (`commit --label step4-...`):\n" + dirty[:1500])

    required = ["README.pdf", "LICENSE.txt", f"reproducibility_report_{a.id}.pdf", "data_hash_report.csv"]
    optional = ["WB-IGO-RIDER.txt", "variable_inventory.csv", "comparison_report.csv"]
    missing = [f for f in required if not (pkg / f).is_file()]
    if not (pkg / a.folder).is_dir():
        missing.append(a.folder + "/")
    if missing and not a.allow_missing:
        sys.exit("ERROR: not in the package folder: " + ", ".join(missing)
                 + ". Add them (and commit), or pass --allow-missing to build the ZIP without them.")

    exclude = [e.strip("/") for e in a.exclude or []]
    members, skipped, excluded = [], [], []
    for top in required + optional:
        if (pkg / top).is_file():
            members.append(top)
    for dirpath, dirnames, filenames in os.walk(pkg / a.folder):
        here = Path(dirpath)
        for d in list(dirnames):
            rel = (here / d).relative_to(pkg).as_posix()
            # the reviewer's own environment (virtualenv, renv library) is never shipped
            if d in NEVER_ZIP or d in SKIP_DIRS or (here.name == "renv" and d in {"library", "staging", "sandbox"}):
                dirnames.remove(d)
                skipped.append(rel + "/")
            elif rel in exclude:
                dirnames.remove(d)
                excluded.append(rel + "/")
        for fn in sorted(filenames):
            rel = (here / fn).relative_to(pkg).as_posix()
            if fn in NEVER_ZIP or fn.startswith("~$"):
                skipped.append(rel)
            elif rel in exclude:
                excluded.append(rel)
            else:
                members.append(rel)
    not_found = [e for e in exclude if not (pkg / e).exists()]
    if not_found:
        sys.exit("ERROR: --exclude path(s) not found (give them relative to the package folder): " + ", ".join(not_found))

    zpath = rep / f"{a.id}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in members:
            zf.write(pkg / rel, rel)
        for e in excluded:  # keep an empty placeholder folder where the data lived
            if e.endswith("/"):
                zf.writestr(e, "")

    # Check the ZIP against the last commit: tracked files by their Git blob id, the rest
    # (files Git ignores) by SHA-256 against the working folder.
    blobs = {}
    for entry in git(pkg, "ls-tree", "-r", "-z", "HEAD").split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            blobs[path] = meta.split()[2]
    rows, mismatches = [], []
    tmp = ev / "_zipcheck"
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            out = Path(zf.extract(info, tmp))
            in_git = info.filename in blobs
            same = git_blob_id(out) == blobs[info.filename] if in_git else sha256(out) == sha256(pkg / info.filename)
            if not same:
                mismatches.append(info.filename)
            rows.append({"file": info.filename, "size_bytes": info.file_size, "sha256": sha256(out),
                         "tracked_by_git": "yes" if in_git else "no", "matches_last_commit": "yes" if same else "NO"})
            out.unlink()
    shutil.rmtree(tmp, ignore_errors=True)
    write_csv(ev / "zip_manifest.csv", ["file", "size_bytes", "sha256", "tracked_by_git", "matches_last_commit"], rows)
    head = git(pkg, "log", "-1", "--format=%h %s").strip()
    check = {"zip": f"report/{a.id}/{a.id}.zip", "zip_sha256": sha256(zpath),
             "built": datetime.now().isoformat(timespec="seconds"), "last_commit": head,
             "files": len(rows), "tracked_by_git": sum(r["tracked_by_git"] == "yes" for r in rows),
             "mismatches": mismatches, "missing": missing, "excluded": excluded, "left_out": skipped}
    (ev / "zip_check.json").write_text(json.dumps(check, indent=2), encoding="utf-8")

    print(f"ZIP: report/{a.id}/{a.id}.zip, {len(rows)} file(s), {zpath.stat().st_size / 1e6:.1f} MB")
    print(f"  SHA-256 {check['zip_sha256']}")
    print(f"  Last commit: {head}. " + ("Every file matches it." if not mismatches
                                        else f"{len(mismatches)} FILE(S) DO NOT MATCH: {mismatches[:10]}"))
    for name, items in (("Excluded (--exclude)", excluded), ("Left out (never shipped)", skipped), ("MISSING", missing)):
        if items:
            print(f"  {name}: " + ", ".join(items[:12]) + (" ..." if len(items) > 12 else ""))
    return 1 if mismatches else 0


def main():
    ap = argparse.ArgumentParser(description="Track what changes in package/[ID]/ during a review.")
    sub = ap.add_subparsers(dest="mode", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--id", required=True, help="Package ID (the folder name under package/)")
        p.add_argument("--root", default=str(DEFAULT_ROOT), help="Path to rrr-package-agent")
        p.set_defaults(fn=fn)
        return p

    p = add("init", cmd_init, "Start local Git tracking and commit the package as received")
    p.add_argument("--raw-data", action="append", help="Raw data folder to ignore, relative to the package (repeatable)")
    p.add_argument("--label", help="Commit label (default: initial-package)")
    p = add("run", cmd_run, "Run the main script, time it, hash every file and commit")
    p.add_argument("--n", type=int, required=True, help="Run number: 1, 2, ...")
    p.add_argument("--cwd", help="Folder to run in, relative to the package (default: the package folder)")
    p.add_argument("--log", action="append", help="The script's own log file, e.g. main.log (repeatable)")
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- then the command, e.g. -- Rscript main.R")
    p = add("compare", cmd_compare, "Compare two runs by SHA-256")
    p.add_argument("--a", type=int, default=1)
    p.add_argument("--b", type=int, default=2)
    p = add("commit", cmd_commit, "Commit everything changed since the last commit under one label")
    p.add_argument("--label", required=True, help="e.g. fix-root-path, step4-license, step4-readme")
    p.add_argument("--note", help="One line on what changed and why")
    add("changes", cmd_changes, "Write AI_CHANGES.md from the history")
    p = add("zip", cmd_zip, "Build report/[ID]/[ID].zip from the package folder and check it against the last commit")
    p.add_argument("--exclude", action="append", help="File or folder to leave out, relative to the package (repeatable)")
    p.add_argument("--folder", default=ZIP_FOLDER, help=f'Code/data folder inside the package (default: "{ZIP_FOLDER}")')
    p.add_argument("--allow-missing", action="store_true", help="Build even if a required top-level file is missing")

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
