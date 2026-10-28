#!/usr/bin/env python3
"""
prepare_publication.py

Automates Skill 4 (prepare package for publication) so I stop doing this
by hand for every RR package. Checks a package folder for what's needed
and fills in whatever's missing:
  - LICENSE.txt
  - WB-IGO-RIDER.txt
  - README.pdf (built from whatever README format exists)
  - data_hash_report.csv
  - reproducibility_report_<PACKAGE_ID>.pdf

Won't touch anything that's already there - if a file exists it's left
alone and just gets reported as ok in the log.

python prepare_publication.py <package_dir> [<report_dir>]

report_dir is optional - if given, prepare_publication_log.md gets dropped
in there next to Mer's other skill outputs (run_log.md, completeness_check.md).

deps: fpdf2, python-docx
"""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# extensions that count as "data" when there's no data/ subfolder to fall back on
DATA_EXTS = {".csv", ".dta", ".rds", ".rdata", ".xlsx", ".xls", ".sav", ".tsv"}

# preference order when hunting for a README - pdf > docx > doc > md > txt
README_EXTS = (".pdf", ".docx", ".doc", ".md", ".txt")


def _plain_text_pdf(text, out_path):
    # fallback - no markdown parsing, just gets words on a page
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    for line in text.splitlines() or [""]:
        safe = line.encode("latin-1", "replace").decode("latin-1")
        pdf.set_x(pdf.l_margin)  # without this, every other line runs out of
        # room and fpdf throws "not enough horizontal space" - hit this on the
        # RR_GEO README, multi_cell computes width from current x not the margin
        if safe.strip():
            pdf.multi_cell(0, 6, safe)
        else:
            pdf.ln(6)
    pdf.output(str(out_path))


# ** has to come before single * or "**bold**" gets read as empty italics
_INLINE_MD = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')


def _inline_md(pdf, text, size=11):
    for chunk in _INLINE_MD.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            pdf.set_font("helvetica", style="B", size=size)
            pdf.write(6, chunk[2:-2])
            pdf.set_font("helvetica", size=size)
        elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            pdf.set_font("courier", size=size - 1)
            pdf.write(6, chunk[1:-1])
            pdf.set_font("helvetica", size=size)
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            pdf.set_font("helvetica", style="I", size=size)
            pdf.write(6, chunk[1:-1])
            pdf.set_font("helvetica", size=size)
        else:
            pdf.write(6, chunk)


def _markdown_pdf(text, out_path):
    # real markdown rendering for .md files, and also for .txt READMEs that
    # turn out to be markdown saved with the wrong extension  
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=11)

    for raw in text.splitlines():
        line = raw.rstrip()
        safe = line.encode("latin-1", "replace").decode("latin-1")
        s = safe.strip()
        pdf.set_x(pdf.l_margin)

        if not s:
            pdf.ln(4)
            continue

        if s in ("---", "***", "___"):
            y = pdf.get_y() + 2
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(6)
            continue

        h = re.match(r'^(#{1,3})\s+(.*)', s)
        if h:
            lvl, txt = len(h.group(1)), h.group(2)
            size = {1: 16, 2: 14, 3: 12}[lvl]
            pdf.set_font("helvetica", style="B", size=size)
            pdf.multi_cell(0, size * 0.6, txt)
            pdf.set_font("helvetica", size=11)
            pdf.ln(2)
            continue

        b = re.match(r'^[-*+]\s+(.*)', s)
        if b:
            # write() wraps continuation lines back to l_margin, not to
            # wherever set_x() left off
            base = pdf.l_margin
            pdf.set_left_margin(base + 5)
            pdf.set_x(base + 5)
            pdf.write(6, "- ")
            _inline_md(pdf, b.group(1))
            pdf.set_left_margin(base)
            pdf.ln(6)
            continue

        _inline_md(pdf, s)
        pdf.ln(6)

    pdf.output(str(out_path))


def _smells_like_markdown(text):
    # rough heuristic for .txt READMEs that are secretly markdown
    hits = 0
    for line in text.splitlines()[:60]:
        s = line.strip()
        if re.match(r'^#{1,6}\s', s) or re.match(r'^[-*+]\s', s) or "**" in s or s.count("`") >= 2:
            hits += 1
    return hits >= 3


def add_license(pkg_dir):
    target = pkg_dir / "LICENSE.txt"
    if target.exists():
        return ["[ok]      LICENSE.txt already present"]
    text = (ASSETS_DIR / "LICENSE_template.txt").read_text(encoding="utf-8")
    text = text.replace("%%YEAR%%", str(datetime.now().year))
    target.write_text(text, encoding="utf-8")
    return ["[created] LICENSE.txt"]


def add_igo_rider(pkg_dir):
    target = pkg_dir / "WB-IGO-RIDER.txt"
    if target.exists():
        return ["[ok]      WB-IGO-RIDER.txt already present"]
    shutil.copyfile(ASSETS_DIR / "WB-IGO-RIDER.txt", target)
    return ["[created] WB-IGO-RIDER.txt"]


def _find_readme(pkg_dir):
    # top level first, then one folder down (some RAs bury it in /code or /docs)
    search_dirs = [pkg_dir] + [p for p in pkg_dir.iterdir() if p.is_dir()]
    for ext in README_EXTS:
        for d in search_dirs:
            hits = [f for f in d.glob(f"*{ext}") if f.stem.lower() == "readme"]
            if hits:
                return hits[0]
    return None


def _docx_to_pdf(source, target):
    # try MS Word automation first 
    try:
        from docx2pdf import convert
        convert(str(source), str(target))
        if target.exists():
            return True
    except Exception:
        pass

    # LibreOffice headless if it's on PATH - this is what actually ends up
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(target.parent), str(source)],
                check=True, capture_output=True, timeout=120,
            )
            produced = target.parent / (source.stem + ".pdf")
            if produced.exists():
                if produced != target:
                    produced.rename(target)
                return True
        except Exception:
            pass

    # last resort: strip the paragraph text and lay it out with fpdf2.
    # loses tables/images but keeps the words - only works for .docx, old
    # binary .doc can't be read this way without a converter
    if source.suffix.lower() == ".docx":
        try:
            import docx
            paras = docx.Document(str(source)).paragraphs
            _plain_text_pdf("\n".join(p.text for p in paras), target)
            return target.exists()
        except Exception:
            return False
    return False


def _md_to_pdf(source, target):
    pandoc = shutil.which("pandoc")
    if pandoc:
        try:
            subprocess.run([pandoc, str(source), "-o", str(target)],
                            check=True, capture_output=True, timeout=120)
            if target.exists():
                return True
        except Exception:
            pass
    text = source.read_text(encoding="utf-8", errors="replace")
    _markdown_pdf(text, target)
    return target.exists()


def prepare_readme(pkg_dir):
    target = pkg_dir / "README.pdf"
    if target.exists():
        return ["[ok]      README.pdf already present at top level"]

    source = _find_readme(pkg_dir)
    if source is None:
        return ["[ACTION]  no README found (checked .pdf/.docx/.doc/.md/.txt) - add one manually"]

    ext = source.suffix.lower()
    try:
        if ext == ".pdf":
            shutil.copyfile(source, target)
            ok = target.exists()
        elif ext in (".docx", ".doc"):
            ok = _docx_to_pdf(source, target)
        elif ext == ".md":
            ok = _md_to_pdf(source, target)
        else:  # .txt
            content = source.read_text(encoding="utf-8", errors="replace")
            if _smells_like_markdown(content):
                _markdown_pdf(content, target)
            else:
                _plain_text_pdf(content, target)
            ok = target.exists()
    except Exception as e:
        return [f"[ACTION]  found {source.name} but the conversion blew up ({e}) "
                f"- convert by hand and save as README.pdf"]

    if ok:
        return [f"[created] README.pdf (from {source.name})"]
    return [f"[ACTION]  found {source.name} but couldn't produce README.pdf "
            f"- convert by hand"]


def generate_data_hash_report(pkg_dir):
    target = pkg_dir / "data_hash_report.csv"
    if target.exists():
        return ["[ok]      data_hash_report.csv already present"]

    data_dir = pkg_dir / "data"
    if data_dir.is_dir():
        base = data_dir
        files = [p for p in sorted(data_dir.rglob("*")) if p.is_file() and not p.name.startswith(".")]
        note = "data/"
    else:
        # no data/ folder - grab anything data-shaped sitting loose in the root.
        # a couple of the older MNG packages are set up this way
        base = pkg_dir
        files = [p for p in sorted(pkg_dir.glob("*")) if p.is_file() and p.suffix.lower() in DATA_EXTS]
        note = "package root (no data/ folder)"
        if not files:
            return [f"[ACTION]  no data/ folder and nothing data-shaped in {pkg_dir} - build this by hand"]

    rows = []
    for path in files:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        rows.append({
            "file": str(path.relative_to(base)),
            "size_bytes": path.stat().st_size,
            "sha256": h.hexdigest(),
            "hashed_on": datetime.now().strftime("%Y-%m-%d"),
        })

    with open(target, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "size_bytes", "sha256", "hashed_on"])
        w.writeheader()
        w.writerows(rows)

    return [f"[created] data_hash_report.csv ({len(rows)} files hashed, {note})"]


def include_reproducibility_report(pkg_dir, report_dir, package_id):
    target = pkg_dir / f"reproducibility_report_{package_id}.pdf"
    if target.exists():
        return [f"[ok]      reproducibility_report_{package_id}.pdf already present"]

    if report_dir and report_dir.exists():
        matches = (
            sorted(report_dir.glob(f"reproducibility_report*{package_id}*.pdf"))
            or sorted(report_dir.glob("reproducibility_report*.pdf"))
            or sorted(report_dir.glob("*report*.pdf"))
        )
        if matches:
            shutil.copyfile(matches[0], target)
            return [f"[created] reproducibility_report_{package_id}.pdf (copied from {matches[0].name})"]

    return [f"[ACTION]  no reproducibility report found - drop "
            f"reproducibility_report_{package_id}.pdf into the package"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python prepare_publication.py <package_dir> [<report_dir>]")
        return 1

    pkg_dir = Path(sys.argv[1]).resolve()
    report_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    package_id = pkg_dir.name  # assumes folder name == package ID, true for everything so far

    if not pkg_dir.is_dir():
        print(f"ERROR: package folder not found: {pkg_dir}")
        return 1

    log = [f"Preparing {package_id} for publication ({pkg_dir})", ""]

    log += add_license(pkg_dir)
    log += add_igo_rider(pkg_dir)
    log += prepare_readme(pkg_dir)
    log += generate_data_hash_report(pkg_dir)
    log += include_reproducibility_report(pkg_dir, report_dir, package_id)

    print("\n".join(log))

    if report_dir:
        report_dir.mkdir(parents=True, exist_ok=True)
        log_path = report_dir / "prepare_publication_log.md"
        log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
        print(f"\nlog saved to {log_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
