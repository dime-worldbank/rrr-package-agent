#!/usr/bin/env python3
"""
Private-data bundle for PRWP reproducibility reviews
----------------------------------------------------
Run this on the secure machine when a package has private data. It builds the
"agent bundle": everything the agent needs, with no data files in it.

    # Before the run (step 1): hash the data, list variables, copy code and docs
    python private_bundle.py prerun  --package "D:/secure/RR_KEN_2026_585" --data data

    # After the two runs (step 2): hash again, compare, copy code diff, outputs, system info
    python private_bundle.py postrun --package "D:/secure/RR_KEN_2026_585" --data data --outputs outputs

--data and --outputs are folders relative to --package and can be repeated.
The bundle goes to rrr-package-agent/package/[ID]/ (the ID is the package folder name;
override with --id, and the repo location with --agent-repo).

Never copied: anything inside the data folders, data-type files anywhere, logs, .git,
hidden files. Notebooks are copied with their cell outputs removed.
Standard library only. Variable inventory needs Rscript (haven, readxl).
"""
import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = SCRIPT_DIR.parents[3]  # .agents/skills/completeness-check/scripts -> repo root
INVENTORY_R = DEFAULT_REPO / ".agents/skills/prepare-publication/assets/variable_inventory.R"

CODE_EXT = {".do", ".ado", ".r", ".rmd", ".qmd", ".py", ".ipynb", ".jl", ".m", ".sh", ".bat",
            ".ps1", ".sps", ".sas", ".rproj", ".stpr", ".yml", ".yaml", ".toml", ".lock", ".cfg",
            ".bib", ".csl", ".tex", ".sty", ".cls", ".lua", ".scss", ".css"}
CODE_NAMES = {"requirements.txt", ".rprofile", "renv.lock", "environment.yml", "makefile", ".here",
              "_quarto.yml", "description"}
KEEP_DOTFILES = {".rprofile", ".here"}
DOC_EXT = {".pdf", ".docx", ".doc", ".md"}
DOC_PREFIXES = ("readme", "license", "das", "data_availability")
OUTPUT_EXT = {".csv", ".tex", ".txt", ".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".xlsx", ".xls"}
SKIP_DIRS = {".git", "__pycache__", "renv", "myenv", ".venv", "venv", "node_modules", "__MACOSX"}
CODE_DIFF_GLOBS = ["*.do", "*.ado", "*.R", "*.r", "*.Rmd", "*.qmd", "*.py", "*.jl", "*.m"]
LARGE_CSV_ROWS = 500


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_data(package, data_dirs, out_csv):
    """Hash every file in the data folders. Same columns as generate_data_hash_report.py."""
    rows = []
    for d in data_dirs:
        root = package / d
        if not root.is_dir():
            sys.exit(f"ERROR: data folder not found: {root}")
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.name.startswith(".") or p.name in {"Thumbs.db", "desktop.ini"}:
                continue
            rows.append({
                "file": p.relative_to(package).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256(p),
                "hashed_on": datetime.now().strftime("%Y-%m-%d"),
            })
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "size_bytes", "sha256", "hashed_on"])
        w.writeheader()
        w.writerows(rows)
    print(f"  Hashed {len(rows)} data file(s) -> {out_csv.name}")
    return rows


def variable_inventory(package, data_dirs, out_csv, rscript):
    """Run variable_inventory.R on each data folder and combine the results (names only, no values)."""
    if not shutil.which(rscript) and not Path(rscript).is_file():
        print(f"  ! Rscript not found ('{rscript}'). Skipped the variable inventory; pass --rscript with the full path.")
        return
    combined = []
    for d in data_dirs:
        tmp = out_csv.with_name(f"_inventory_{abs(hash(d))}.csv")
        res = subprocess.run([rscript, str(INVENTORY_R), str(package / d), str(tmp)],
                             capture_output=True, text=True)
        if res.returncode != 0 or not tmp.exists():
            print(f"  ! Variable inventory failed for {d}: {res.stderr.strip()[-300:]}")
            continue
        with open(tmp, newline="", encoding="utf-8") as f:
            combined.extend(csv.DictReader(f))
        tmp.unlink()
    if combined:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(combined[0].keys()))
            w.writeheader()
            w.writerows(combined)
        print(f"  Listed variables for {len(combined)} dataset(s) -> {out_csv.name}")


def strip_notebook(src, dst):
    """Copy a notebook without cell outputs, which can contain printed data."""
    nb = json.loads(src.read_text(encoding="utf-8"))
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    dst.write_text(json.dumps(nb, indent=1), encoding="utf-8")


def is_code_or_doc(p):
    ext, name = p.suffix.lower(), p.name.lower()
    if ext in CODE_EXT or name in CODE_NAMES:
        return True
    if ext in DOC_EXT:
        return True
    return ext == ".txt" and name.startswith(DOC_PREFIXES)


def walk(package, exclude):
    for dirpath, dirnames, filenames in os.walk(package):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(".")
                       and (here / d).resolve() not in exclude]
        for fn in filenames:
            if not fn.startswith(".") or fn.lower() in KEEP_DOTFILES:
                yield here / fn


def copy_code(package, data_dirs, output_dirs, bundle):
    """Copy code and documentation, never data. Returns (copied, skipped) relative paths."""
    exclude = {(package / d).resolve() for d in data_dirs + output_dirs}
    exclude.add(bundle.resolve())
    copied, skipped = [], []
    for p in walk(package, exclude):
        rel = p.relative_to(package)
        if p.suffix.lower() in {".log", ".smcl"} or not is_code_or_doc(p):
            skipped.append(rel.as_posix())
            continue
        dst = bundle / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".ipynb":
            strip_notebook(p, dst)
        else:
            shutil.copy2(p, dst)
        copied.append(rel.as_posix())
    return copied, skipped


def copy_outputs(package, output_dirs, bundle):
    copied, warnings = [], []
    for d in output_dirs:
        root = package / d
        if not root.is_dir():
            print(f"  ! Outputs folder not found: {root}")
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in OUTPUT_EXT:
                continue
            rel = p.relative_to(package)
            if p.suffix.lower() == ".csv":
                with open(p, encoding="utf-8", errors="ignore") as f:
                    n = sum(1 for _ in f)
                if n > LARGE_CSV_ROWS:
                    warnings.append(f"{rel.as_posix()} has {n} rows; it may be microdata, not a table. Not copied.")
                    continue
            dst = bundle / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            copied.append(rel.as_posix())
    return copied, warnings


def compare_hashes(pre_csv, post_csv, out_csv):
    def load(path):
        with open(path, newline="", encoding="utf-8") as f:
            return {r["file"]: r["sha256"] for r in csv.DictReader(f)}
    pre, post = load(pre_csv), load(post_csv)
    rows = []
    for f in sorted(set(pre) | set(post)):
        if f in pre and f in post:
            status = "input (unchanged)" if pre[f] == post[f] else "generated (changed by the code)"
        elif f in post:
            status = "generated (new)"
        else:
            status = "removed during run"
        rows.append({"file": f, "status": status})
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "status"])
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("  Hash comparison -> " + out_csv.name + ": " + ", ".join(f"{v} {k}" for k, v in counts.items()))


def code_diff(package, out_file):
    if not (package / ".git").exists():
        print("  ! No local Git repo in the package; skipped code_changes.diff.")
        return
    try:
        root = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=package,
                              capture_output=True, text=True, check=True).stdout.split()[0]
        diff = subprocess.run(["git", "diff", root, "HEAD", "--", *CODE_DIFF_GLOBS], cwd=package,
                              capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
        print(f"  ! Could not build code_changes.diff: {e}")
        return
    out_file.write_text(diff, encoding="utf-8")
    n = sum(1 for line in diff.splitlines() if line.startswith("diff --git"))
    print(f"  Code changes since the initial commit: {n} file(s) -> {out_file.name}")


def system_info(out_file):
    cpu, mem = platform.processor() or platform.machine(), ""
    try:
        if sys.platform == "darwin":
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip() or cpu
            mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout)
        elif sys.platform.startswith("win"):
            import ctypes

            class MEMSTAT(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MEMSTAT()
            m.dwLength = ctypes.sizeof(MEMSTAT)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            mem = m.ullTotalPhys
        else:
            with open("/proc/meminfo") as f:
                mem = int(f.readline().split()[1]) * 1024
    except Exception:
        pass
    mem_txt = f"{mem / 1024**3:.1f} GB" if mem else "unknown"
    text = (f"Operating System: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"Processor:        {cpu}\n"
            f"Memory:           {mem_txt}\n"
            f"Software:         [fill in, e.g. Stata 18.0 MP]\n"
            f"Runtime (run 1):  [fill in]\n"
            f"Stability:        [fill in]\n")
    out_file.write_text(text, encoding="utf-8")
    print(f"  System specs -> {out_file.name} (add software version and runtime)")


def write_manifest(bundle, name, sections):
    with open(bundle / name, "w", encoding="utf-8") as f:
        f.write(f"# Agent bundle manifest — {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write("# Skim the COPIED list before starting the agent: no data, no names, no hard-coded values.\n\n")
        for title, items in sections:
            f.write(f"## {title} ({len(items)})\n")
            f.writelines(f"{i}\n" for i in items)
            f.write("\n")


def main():
    ap = argparse.ArgumentParser(description="Build the agent bundle for a package with private data.")
    ap.add_argument("mode", choices=["prerun", "postrun"])
    ap.add_argument("--package", required=True, help="Package root on the secure machine")
    ap.add_argument("--data", action="append", required=True, help="Data folder relative to the package (repeatable)")
    ap.add_argument("--outputs", action="append", default=[], help="Outputs folder relative to the package (postrun, repeatable)")
    ap.add_argument("--id", help="Package ID (default: the package folder name)")
    ap.add_argument("--agent-repo", default=str(DEFAULT_REPO), help="Path to rrr-package-agent")
    ap.add_argument("--rscript", default="Rscript", help="Rscript executable, if not on PATH")
    a = ap.parse_args()

    package = Path(a.package).resolve()
    pkg_id = a.id or package.name
    bundle = Path(a.agent_repo).resolve() / "package" / pkg_id
    if bundle.resolve() == package or package in bundle.resolve().parents:
        sys.exit("ERROR: the bundle folder is inside the secure package. Keep the package outside rrr-package-agent.")
    bundle.mkdir(parents=True, exist_ok=True)
    print(f"Package: {package}\nBundle:  {bundle}\n")

    if a.mode == "prerun":
        hash_data(package, a.data, bundle / "data_hash_report_prerun.csv")
        variable_inventory(package, a.data, bundle / "variable_inventory.csv", a.rscript)
        copied, skipped = copy_code(package, a.data, a.outputs, bundle)
        write_manifest(bundle, "bundle_manifest_prerun.txt", [("COPIED", copied), ("NOT COPIED", skipped)])
        print(f"  Copied {len(copied)} code/doc file(s); left out {len(skipped)} (see bundle_manifest_prerun.txt)")
        print("\nNext: skim the manifest, then start step 1 in the agent chat (private data mode).")
    else:
        pre = bundle / "data_hash_report_prerun.csv"
        if not pre.exists():
            sys.exit("ERROR: data_hash_report_prerun.csv not found in the bundle. Run 'prerun' first.")
        hash_data(package, a.data, bundle / "data_hash_report_postrun.csv")
        compare_hashes(pre, bundle / "data_hash_report_postrun.csv", bundle / "hash_comparison.csv")
        code_diff(package, bundle / "code_changes.diff")
        copied, skipped = copy_code(package, a.data, a.outputs, bundle)
        out_copied, warnings = copy_outputs(package, a.outputs, bundle)
        system_info(bundle / "system_info.txt")
        write_manifest(bundle, "bundle_manifest_postrun.txt",
                       [("CODE/DOCS COPIED", copied), ("OUTPUTS COPIED", out_copied), ("NOT COPIED", skipped + warnings)])
        print(f"  Copied {len(out_copied)} output file(s)")
        for w in warnings:
            print(f"  ! {w}")
        print("\nNext: fill in system_info.txt, then paste the 'after the run' prompt in the agent chat.")


if __name__ == "__main__":
    main()
