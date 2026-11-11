"""Export a Markdown verification report to PDF with headless Chrome/Edge.

Usage:
    python md_to_pdf.py report/RR_XXX/verification_report_RR_XXX.md [output.pdf]

Default output: reproducibility_report_[PACKAGE_ID].pdf next to the .md.
Internal links (Contents -> sections) stay clickable in the PDF.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

# Close to the tufte-handout look of the LaTeX report: serif, black text, black links
CSS = """
@page { size: Letter; margin: 1in; }
body { font-family: "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
       font-size: 11pt; line-height: 1.4; color: #000; background: #fff; }
h1 { font-size: 20pt; font-weight: normal; margin: 0.4em 0; }
h2 { font-size: 15pt; font-weight: normal; font-style: italic; margin: 1.4em 0 0.5em; }
h3 { font-size: 13pt; font-weight: normal; margin: 0.3em 0; }
a { color: inherit; text-decoration: none; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.92em; }
li { margin: 0.2em 0; }
img { max-width: 100%; }
table { border-collapse: collapse; margin: 0.8em auto; }
th, td { border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 3px 8px; }
"""


def find_browser():
    for path in BROWSERS:
        if os.path.exists(path):
            return path
    sys.exit("Chrome or Edge not found.")


def main():
    md_path = Path(sys.argv[1]).resolve()
    if len(sys.argv) > 2:
        pdf_path = Path(sys.argv[2]).resolve()
    else:
        package_id = md_path.stem.replace("verification_report_", "")
        pdf_path = md_path.parent / f"reproducibility_report_{package_id}.pdf"

    # The browser fails silently if the PDF is locked (e.g. open in a viewer)
    if pdf_path.exists():
        try:
            open(pdf_path, "ab").close()
        except OSError:
            sys.exit(f"{pdf_path.name} is open in another program. Close it and rerun.")

    text = md_path.read_text(encoding="utf-8")
    # Drop YAML front matter (e.g. an RStudio "output:" header)
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    # Python-Markdown needs 4-space indents for nested lists; reports use 2
    text = re.sub(r"^( +)", lambda m: m.group(1) * 2, text, flags=re.M)
    body = markdown.markdown(text, extensions=["extra", "sane_lists"])

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{md_path.parent.as_uri()}/">
<title>{md_path.stem}</title><style>{CSS}</style></head>
<body>{body}</body></html>"""

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "report.html"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [find_browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
             "--allow-file-access-from-files", f"--user-data-dir={tmp}\\profile",
             f"--print-to-pdf={pdf_path}", html_path.as_uri()],
            check=True, capture_output=True,
        )
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
