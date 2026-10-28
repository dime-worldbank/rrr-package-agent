---
name: paper-tables-to-latex
description: >-
  Extract every table from a research paper PDF and reproduce each one as LaTeX
  that matches the source layout, saving all tables into a single combined .tex
  file. Use this whenever the user wants to pull tables, results tables, or
  tabular data out of a paper, preprint, report, or scientific PDF and get LaTeX
  back — including phrasings like "get the tables from this paper", "convert the
  results tables to LaTeX", "extract the tables in this pdf", "reproduce Table 3
  in LaTeX", or "I need the tables from this arXiv paper as .tex". Works on
  digital and scanned/image-only PDFs because it reads the tables visually with
  Claude's vision, so it also applies when text copy-paste from the PDF produced
  garbled or misaligned columns. Trigger even if the user does not say the word
  "vision" or name a specific table.
---

# Paper Tables → LaTeX

Extract **every** table from a research-paper PDF and reproduce each as LaTeX
that **matches the source layout**, collected into **one combined `.tex` file**
that compiles on its own.

## Why read tables visually

Tables in papers are 2‑D visual objects: spanning headers, grouped columns,
mixed rule styles, footnotes, sub/superscripts, bolded best results, rotated
(landscape) layouts, and cells that wrap. Copying text out of a PDF almost
always scrambles column alignment and silently drops this structure, and it
fails entirely on scanned/image PDFs. Rendering each page to a high‑resolution
image and transcribing what you *see* preserves the real structure and the exact
numbers — which is the whole point of extracting a results table. So this skill
always works from rendered page images, not from copied PDF text.

## Inputs and output

- **Input:** one or more PDF files (paths provided by the user, in the uploads
  folder, or in the connected workspace folder).
- **Output:** for each PDF, a single file `<pdfname>_tables.tex` containing all
  tables in document order, plus (if a LaTeX engine is available) the compiled
  `<pdfname>_tables.pdf` so the user can eyeball fidelity. Save both to the
  output/workspace folder and present the `.tex`.

## Workflow

Follow these steps in order. Do not skip the render step (step 1) or the
validation step (step 5) — they are what make the result trustworthy.

### 1. Render the PDF pages to images

Render every page to a PNG so you can read it visually:

```bash
python scripts/render_pdf.py "<paper.pdf>" --dpi 200 --out <workdir>/pages
```

The script prints a JSON summary (page count and the list of PNG paths). Use
~200 DPI as a default; footnotes, subscripts, and dense numeric tables become
unreadable below that. If a specific table is still hard to read, re-render just
that page at higher resolution (see step 3).

If the script reports a missing dependency, install it with
`pip install pymupdf` (preferred) or ensure `poppler` is available for the
`pdf2image` fallback.

### 2. Locate every table

View the page images in order (Read tool) and build an inventory of **all**
tables. Because the user asked for every table, be inclusive:

- anything with a "Table N" caption, in the body **or** appendices/supplement;
- unlabeled tabular displays (e.g. a small comparison block with no "Table"
  caption) — if it reads as a table, include it;
- tables that continue across a page break or across two columns — treat the
  pieces as one table.

For each table, note: its number/label, full caption, the page(s) it sits on,
whether it is rotated (landscape), and whether it spans pages. When in doubt
about whether a display counts as a table, include it.

### 3. Transcribe each table to LaTeX (match the source)

For each table, look closely at its page image and reproduce the **visual
layout**, not an "improved" version. Before writing anything nontrivial, read
`references/latex_conventions.md` — it covers merged cells, grouped headers,
footnotes, math, escaping, rotation, and multi-page tables with worked examples.

Core fidelity rules:

- **Match the rule style you see.** Horizontal-only rules → `booktabs`
  (`\toprule/\midrule/\bottomrule`, `\cmidrule` for header groups). A full grid
  with vertical lines → `\hline` and `|` in the column spec. Don't convert one
  style into the other.
- **Preserve structure exactly:** same row and column order, spanning cells via
  `\multicolumn` / `\multirow`, grouped column headers, and the same alignment
  (l/c/r; `p{}` for wrapping cells).
- **Preserve the data verbatim:** exact numbers, decimal places, `±`, `%`, units,
  and any **bold** on best results (`\textbf{}`). These details are the result.
- **Keep the caption and number.** Use `\caption{...}` with the paper's wording
  and `\label{tab:N}` matching the table number.
- **Never invent a value.** If a cell is genuinely illegible after re-rendering
  that page at higher DPI (e.g. `--page N --dpi 400`), transcribe your best read
  and leave a `% TODO: verify` comment on that line rather than guessing.

### 4. Assemble one combined `.tex`

Write all tables, in document order, into a single self-contained file. Use this
structure so it compiles standalone yet the tables can be pasted into the user's
own document unchanged:

```latex
% Tables auto-extracted from <paper.pdf>
% Compile: latexmk -pdf <pdfname>_tables.tex   (or: pdflatex <pdfname>_tables.tex)
\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs, multirow, array, graphicx, amsmath, rotating}
\usepackage[table]{xcolor}   % only if the source uses cell shading
% \usepackage{siunitx}       % optional: for decimal-aligned numeric columns
\begin{document}

% ===== Table 1 (p.3) — <short caption> =====
\begin{table}[htbp]\centering
\caption{<full caption text>}
\label{tab:1}
\begin{tabular}{...}
\toprule
...
\bottomrule
\end{tabular}
\end{table}

% ===== Table 2 (p.5) — ... =====
...

\end{document}
```

Only load packages the tables actually use, but it's fine to keep the common set
above. Add a one-line `% ===== Table N (page) — caption =====` banner before each
table so the file is easy to navigate.

### 5. Validate by compiling

A table that doesn't compile isn't done. Run:

```bash
python scripts/validate_latex.py "<pdfname>_tables.tex"
```

It compiles the file and prints any LaTeX errors with line numbers. Fix the
common culprits — unescaped `& % _ # $`, a `\multicolumn` whose span doesn't add
up, a column-count mismatch, or a missing package — and re-run until it compiles
cleanly. If no LaTeX engine is installed, the script says so; in that case do a
careful manual check that every row has the right number of `&` for its column
spec and that all specials are escaped.

### 6. Deliver

Save `<pdfname>_tables.tex` (and the compiled PDF if produced) to the output
folder, present the `.tex` file, and give a short inventory: how many tables were
found and a one-line caption for each, flagging any `% TODO: verify` cells so the
user knows where to double-check.

## Handling multiple PDFs

Process each PDF independently and produce one combined `.tex` per paper (named
after that PDF). Don't merge tables from different papers into one file unless the
user explicitly asks for that.
