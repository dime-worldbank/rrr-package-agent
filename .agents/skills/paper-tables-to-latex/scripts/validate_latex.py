#!/usr/bin/env python3
"""Compile a .tex file to catch table transcription errors.

A results table that doesn't compile isn't finished, so run this on the combined
.tex before delivering. It compiles in a temp directory (so it never litters the
output folder with .aux/.log junk) and reports the LaTeX errors with line numbers
so they're easy to fix. If it succeeds, it copies the produced PDF next to the
.tex so the user can eyeball fidelity against the paper.

Usage:
  python validate_latex.py tables.tex
  python validate_latex.py tables.tex --engine pdflatex
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile


def find_engine(preferred=None):
    candidates = [preferred] if preferred else []
    candidates += ["latexmk", "pdflatex", "tectonic"]
    for eng in candidates:
        if eng and shutil.which(eng):
            return eng
    return None


def build_cmd(engine, tex_name, workdir):
    if engine == "latexmk":
        return ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                f"-outdir={workdir}", tex_name]
    if engine == "pdflatex":
        return ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                f"-output-directory={workdir}", tex_name]
    if engine == "tectonic":
        return ["tectonic", "--outdir", workdir, tex_name]
    raise ValueError(engine)


def extract_errors(log_text):
    """Pull the useful lines out of a LaTeX log: '! ...' errors and 'l.NN' lines."""
    errors = []
    lines = log_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("!"):
            context = [line]
            for j in range(i + 1, min(i + 6, len(lines))):
                context.append(lines[j])
                if lines[j].startswith("l."):
                    break
            errors.append("\n".join(context))
    # Also surface undefined control sequences / missing packages succinctly.
    for m in re.finditer(r"! LaTeX Error: File `([^']+)' not found", log_text):
        errors.append(f"Missing package/file: {m.group(1)} (add the \\usepackage or install it)")
    return errors


def main():
    ap = argparse.ArgumentParser(description="Compile a .tex file and report errors.")
    ap.add_argument("tex", help="Path to the .tex file to validate.")
    ap.add_argument("--engine", help="Force an engine: latexmk | pdflatex | tectonic.")
    args = ap.parse_args()

    tex_path = os.path.abspath(args.tex)
    if not os.path.isfile(tex_path):
        print(f"ERROR: file not found: {tex_path}")
        sys.exit(2)

    engine = find_engine(args.engine)
    if not engine:
        print("SKIPPED: no LaTeX engine found (latexmk / pdflatex / tectonic).")
        print("Validation skipped. Manually check: every row has the right number of '&',")
        print("all of & % _ # $ are escaped, and every \\multicolumn span adds up.")
        sys.exit(0)

    tex_dir = os.path.dirname(tex_path)
    tex_name = os.path.basename(tex_path)

    with tempfile.TemporaryDirectory() as workdir:
        cmd = build_cmd(engine, tex_name, workdir)
        proc = subprocess.run(cmd, cwd=tex_dir, capture_output=True, text=True)

        log_text = proc.stdout + "\n" + proc.stderr
        # latexmk/pdflatex also write a .log in the workdir; prefer that if present.
        log_file = os.path.join(workdir, os.path.splitext(tex_name)[0] + ".log")
        if os.path.isfile(log_file):
            with open(log_file, "r", errors="ignore") as f:
                log_text = f.read()

        produced_pdf = os.path.join(workdir, os.path.splitext(tex_name)[0] + ".pdf")
        ok = os.path.isfile(produced_pdf) and proc.returncode == 0

        if ok:
            dest = os.path.join(tex_dir, os.path.splitext(tex_name)[0] + ".pdf")
            shutil.copyfile(produced_pdf, dest)
            print(f"OK: compiled cleanly with {engine}.")
            print(f"PDF written to: {dest}")
            print("Open it and compare each table against the paper to confirm fidelity.")
            sys.exit(0)
        else:
            print(f"FAILED: {engine} could not compile {tex_name}.\n")
            errs = extract_errors(log_text)
            if errs:
                print("LaTeX errors (fix these, then re-run):\n")
                for e in errs[:25]:
                    print("  " + e.replace("\n", "\n  "))
                    print()
            else:
                print("No '!' errors parsed; tail of the log:\n")
                print("\n".join(log_text.splitlines()[-30:]))
            sys.exit(1)


if __name__ == "__main__":
    main()
