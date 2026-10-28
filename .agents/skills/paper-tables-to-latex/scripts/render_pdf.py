#!/usr/bin/env python3
"""Render PDF pages to PNG images so tables can be read visually.

The whole reason this skill renders to images instead of copying text is that
table structure (spanning headers, alignment, footnotes, bold) survives as
pixels but not as extracted text. Read the PNGs this produces, then transcribe.

Backends, in order of preference:
  1. PyMuPDF (``import fitz``)  -- pip install pymupdf   (no system deps)
  2. pdf2image                  -- pip install pdf2image + system ``poppler``

Usage:
  python render_pdf.py paper.pdf                      # all pages @200 DPI -> ./pages
  python render_pdf.py paper.pdf --dpi 300 --out out  # higher res, custom dir
  python render_pdf.py paper.pdf --pages 3-5          # a page range (1-based)
  python render_pdf.py paper.pdf --page 4 --dpi 400   # one page, zoom in on a dense table

Prints a JSON summary: {"pdf", "num_pages", "dpi", "out_dir", "files":[...]}.
"""
import argparse
import json
import os
import sys


def parse_pages(spec, num_pages):
    """Turn '3-5', '4', '1,4,7-9' into a sorted list of 1-based page numbers."""
    if not spec:
        return list(range(1, num_pages + 1))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            pages.update(range(min(a, b), max(a, b) + 1))
        else:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= num_pages)


def render_with_fitz(pdf_path, out_dir, dpi, pages):
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    num_pages = doc.page_count
    wanted = parse_pages(pages, num_pages)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    files = []
    for p in wanted:
        page = doc.load_page(p - 1)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        fname = os.path.join(out_dir, f"page-{p:03d}.png")
        pix.save(fname)
        files.append(fname)
    doc.close()
    return num_pages, files


def render_with_pdf2image(pdf_path, out_dir, dpi, pages):
    from pdf2image import convert_from_path, pdfinfo_from_path

    info = pdfinfo_from_path(pdf_path)
    num_pages = int(info["Pages"])
    wanted = parse_pages(pages, num_pages)
    files = []
    for p in wanted:
        images = convert_from_path(pdf_path, dpi=dpi, first_page=p, last_page=p)
        fname = os.path.join(out_dir, f"page-{p:03d}.png")
        images[0].save(fname, "PNG")
        files.append(fname)
    return num_pages, files


def main():
    ap = argparse.ArgumentParser(description="Render PDF pages to PNGs for visual table extraction.")
    ap.add_argument("pdf", help="Path to the PDF file.")
    ap.add_argument("--dpi", type=int, default=200, help="Render resolution (default 200; use 300-400 to zoom dense tables).")
    ap.add_argument("--out", default="pages", help="Output directory for PNGs (default ./pages).")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--pages", help="Page range/list, 1-based, e.g. '3-5' or '1,4,7-9'.")
    group.add_argument("--page", type=int, help="Render a single page (1-based).")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        print(json.dumps({"error": f"file not found: {args.pdf}"}))
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    pages_spec = str(args.page) if args.page else args.pages

    errors = []
    for backend, fn in (("pymupdf", render_with_fitz), ("pdf2image", render_with_pdf2image)):
        try:
            num_pages, files = fn(args.pdf, args.out, args.dpi, pages_spec)
            print(json.dumps({
                "pdf": os.path.abspath(args.pdf),
                "backend": backend,
                "num_pages": num_pages,
                "dpi": args.dpi,
                "out_dir": os.path.abspath(args.out),
                "rendered": len(files),
                "files": files,
            }, indent=2))
            return
        except ImportError as e:
            errors.append(f"{backend}: {e}")
        except Exception as e:  # pragma: no cover - backend runtime failure
            errors.append(f"{backend}: {type(e).__name__}: {e}")

    print(json.dumps({
        "error": "No working PDF render backend.",
        "detail": errors,
        "fix": "pip install pymupdf   (preferred), or  pip install pdf2image  plus a system 'poppler' install.",
    }, indent=2))
    sys.exit(1)


if __name__ == "__main__":
    main()
