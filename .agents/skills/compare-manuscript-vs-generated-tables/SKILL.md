---
name: compare-manuscript-vs-generated-tables
description: >
  Automate exhibit verification by comparing manuscript tables AND figures
  (both extracted from the paper PDF) against package-generated outputs from
  Step 2 for any PRWP package. Generated outputs may be numeric formats
  (.xlsx, .csv, .txt, .tsv, .tex) or visual formats (.png, .jpg, .pdf) - this
  skill handles both. A generated .pdf table is compared automatically via
  its text layer when one exists (e.g. R's gt::gtsave()); only a genuinely
  scanned/image-only PDF, or a plotted figure, falls back to manual Claude
  vision comparison. Trigger when reviewers ask "compare tables", "compare
  figures", "check if paper exhibits match outputs", "automate exhibit
  comparison", "table-by-table verification", "verify consistency with the
  manuscript", "compare table1.pdf to the manuscript", or "step 3 compare
  exhibits".
---

# Skill — Compare Manuscript Exhibits vs Generated Outputs

## What this skill does
Verifies every exhibit (table **and** figure) in the manuscript against what
Step 2 actually generated. It covers protocol step "Verify Consistency with
the Manuscript" and feeds directly into `create-report`'s exhibit list.

Three comparison paths, because manuscript extraction is always LaTeX but
package-generated outputs are not:

1. **Numeric tables** (script-automated) — generated outputs in `.xlsx`,
   `.txt`, `.csv`, `.tsv`, `.tex`, `.log`, `.html`/`.htm`, or `.rtf` are parsed
   and compared value-by-value against the manuscript LaTeX tables.
2. **PDF tables with a text layer** (script-automated) — a `.pdf` table
   export (e.g. R's `gt::gtsave()`, which is usually a real headless-browser
   print, not a rasterized image) has its text extracted directly and is
   compared the same way as the formats above. Only a `.pdf` with no
   extractable text (a scanned/rasterized PDF) falls back to path 3.
3. **Figures and non-text-extractable visual outputs** (Claude vision,
   manual) — `.png`/`.jpg` figures, and any `.pdf` where text extraction
   failed or found nothing, can't be parsed numerically. These are
   enumerated by the script but judged by viewing the image side-by-side
   with the rendered manuscript page. See "Figure and visual-output
   comparison" below.
4. **Anything else** (catch-all, manual triage) — a file whose format isn't
   recognized by any path above (`.docx`, `.json`, a typo'd extension, etc.)
   is still listed explicitly, under "Unclassified outputs", rather than
   silently disappearing from the report.

Because package-generated outputs come in far more formats than the always-
LaTeX manuscript extraction, **every file in the outputs folder ends up in
exactly one of these buckets** — auto-verified (including text-extractable
PDFs), queued for visual review, or flagged as unclassified. None can go
unaccounted for.

Produces:
- a simple, reviewer-friendly Markdown verification summary covering tables,
  a to-do list of figures/visual outputs still needing a visual verdict, and
  any unclassified files needing manual triage,
- a JSON artifact with diagnostics and per-table reasons,
- an explicit Step 2 execution gate (`comparison skipped` when code failed).

This skill must only compare against artifacts generated in Step 2.

---

## Inputs expected
- `PACKAGE_ID` (e.g., `RR_WLD_2026_641`)
- Manuscript tables file (combined `.tex`):
  - usually `report/<PACKAGE_ID>/paper_tables/*_tables.tex`
- Rendered manuscript page images (for figure comparison):
  - usually `report/<PACKAGE_ID>/paper_tables/pages/page-*.png`
  - produced by `paper-tables-to-latex`'s `scripts/render_pdf.py`
- Generated outputs folder from Step 2 run:
  - usually `package/<PACKAGE_ID>/outputs/` or `package/<PACKAGE_ID>/outputs/tables/`
- Step 2 run evidence:
  - `report/<PACKAGE_ID>/run_log.md` or `report/<PACKAGE_ID>/run_log.txt`

If the manuscript combined `.tex` or the rendered page images do not exist yet,
run skill `paper-tables-to-latex` first — it produces both from the same PDF.

---

## Automation script
Script path:
- `scripts/compare_tables.py`

### What it compares
- Checks Step 2 run status first. If execution failed, it stops comparison and reports the failure reason.
- Extracts each table from manuscript `.tex` in document order.
- Parses numeric values from each manuscript table.
- Parses manuscript row labels from table bodies.
- Reads generated output table files (`.xlsx`, `.txt`, `.csv`, `.tsv`, `.tex`,
  `.log`, `.html`/`.htm`, `.rtf`). HTML and RTF markup is stripped (tags /
  control words) before numbers and row labels are extracted — this covers
  `outreg2`'s `.rtf` export and `stargazer`'s `type="html"` export, which are
  common in Stata/R packages.
- For every `.pdf` in the outputs folder, tries to extract its text layer
  (via PyMuPDF) and parse it the same way. This works for real text-layer
  PDFs (`gt::gtsave()`, `graph export ... , as(pdf)`, etc.) — only lines that
  are *purely* numeric are read as data, so digits embedded in header/title
  text (e.g. a "Duration2011" column header) aren't mistaken for values. A
  `.pdf` with no extractable text (a scanned/rasterized image) is routed to
  the visual-review bucket instead — nothing is force-fit.
- Pairs each manuscript table with its output by the table label the output
  filename encodes (`table3.txt` → Table 3, `tableA1.txt` → Table A1, and the
  same for `table1.pdf`), not by raw alphabetical order — this avoids a
  non-table numeric file (e.g. a figure's underlying-data CSV) shifting every
  later pairing by one. A table with a known label but no matching output is
  left unmatched rather than guessing.
- Applies exact numeric comparison with tolerance and row-label checks.
- Flags each table as:
  - `Verified` (exact match within tolerance and no missing manuscript rows)
  - `Not verified` (differences, missing rows, missing files, or insufficient data)
- Any `.png`, `.jpg`, `.jpeg`, or non-text-extractable `.pdf` is listed in the
  report and JSON (`visual_review_outputs`) but never fed into the numeric
  pairing, so it can't silently shift which manuscript table gets paired with
  which numeric file.
- Anything left over (matched by neither path above — e.g. `.docx`, `.json`,
  an unanticipated export format) is listed under **unclassified outputs**
  (`unclassified_outputs` in JSON) instead of being silently dropped.

The report is intentionally simple, for example:

```text
Results in the Main Section of the Paper
- Table 1 Verified. Verified against table1.txt.
- Table 2 Not verified. Compared against table2.txt. Reason: numeric differences.

Results in the Annex
- Table A1 Verified. Verified against tableA1.txt.
```

---

## Usage
From repository root:

```bash
python .agents/skills/compare-manuscript-vs-generated-tables/scripts/compare_tables.py \
  --package-id RR_WLD_2026_641 \
  --paper-tex report/RR_WLD_2026_641/paper_tables/Vergara_cyber_april2026_tables.tex \
  --outputs-dir package/RR_WLD_2026_641/outputs/tables \
  --step2-log report/RR_WLD_2026_641/run_log.md \
  --report-out report/RR_WLD_2026_641/table_comparison_report.md \
  --json-out report/RR_WLD_2026_641/table_comparison_report.json
```

If `openpyxl` is missing:

```bash
pip install openpyxl
```

PDF text-extraction is optional — without `pymupdf` installed, every `.pdf`
output simply falls back to the visual-review bucket (the old behavior),
rather than the script failing:

```bash
pip install pymupdf
```

---

## Output interpretation and reviewer action
Use this output directly when drafting exhibit findings:
- If Step 2 failed, report `Could not verify` and include the failure reason from the run log.
- If all tables are `Verified`, state that findings are verified.
- Any `Not verified` item must include a short reason in the report.
- Every entry under "Figures and PDF/image outputs" must be resolved manually
  (see next section) before the exhibit list is complete — don't leave these
  as an unstated gap in the report.
- Every entry under "Unclassified outputs" must be triaged too: open the file,
  determine whether it's an exhibit (compare it manually) or something that
  doesn't need a verdict (e.g. a log file, a manifest), and say which in the
  report — don't leave it as a bare filename.

Always confirm final exhibit status manually in `verification_report_<PACKAGE_ID>.tex`.

---

## Figure and visual-output comparison (manual, Claude vision)

Figures, and any PDF whose text couldn't be extracted (a scanned/rasterized
export - a real text-layer PDF table is auto-compared already, see above),
can't be diffed numerically — they're judged the same way a human reviewer
would: look at both images and decide if they match. Do this for every file
listed under `visual_review_outputs` in the JSON / "Figures and PDF/image
outputs" in the Markdown report.

1. **Make sure manuscript page renders exist.** If
   `report/<PACKAGE_ID>/paper_tables/pages/` is missing or empty, run
   `paper-tables-to-latex`'s render step first:
   ```bash
   python .agents/skills/paper-tables-to-latex/scripts/render_pdf.py "<paper.pdf>" \
     --dpi 200 --out report/<PACKAGE_ID>/paper_tables/pages
   ```
2. **Identify which exhibit each visual output corresponds to.** Generated
   filenames are usually self-describing (`Figure2A.png`, `table1.pdf`) — map
   each to a "Figure N" / "Table N" label. If the filename is ambiguous, open
   the generating script's output call (e.g. `ggsave(...)`, `graph export
   ...`, `esttab ... using`) to confirm which exhibit it produces.
3. **Find that exhibit on the rendered manuscript pages.** Use the Read tool
   to view the page PNGs in order (they were already inventoried while
   extracting tables) until you find the matching caption/label.
4. **View both images and judge the match.** Use the Read tool on the
   manuscript page image and on the generated output file (render a `.pdf`
   output to PNG first with `render_pdf.py` if needed). Compare:
   - **Figures:** same axes, scale, legend/series, number of bars/lines,
     visible trend/shape, and any labeled values.
   - **Table images/PDFs:** same row/column structure, numbers, signs,
     significance stars, and rounding consistent with the manuscript.
5. **Record a verdict** using the same vocabulary as the numeric tables —
   `Verified` / `Not verified` plus a one-line reason — and add it to the
   Markdown report in place of the raw filename listing. This is a manual
   edit to the script's draft output, not something the script computes.

---

## Limitations
- Label-based matching relies on `\label{tab:N}` in the manuscript `.tex` and a recognizable table token in the output filename; a table/file with neither falls back to positional order, which can mispair if either side uses fully generic naming.
- Row-label detection is heuristic and works best when manuscript and outputs use comparable first-column row labels.
- Complex multi-panel layouts or heavily formatted tables may lower parser accuracy.
- Non-numeric evidence (labels, footnotes, stars, signs, confidence intervals formatting) still requires human review.
- PDF text extraction reads only lines that are purely numeric as data, and needs `pymupdf`; without it, or for a scanned/rasterized PDF, that table falls back to manual Claude-vision comparison, not a computed verdict.
- Figure comparison (and any non-text-extractable PDF) is entirely manual (Claude vision) — the script only enumerates candidates, it does not compute a verdict for them.

---

## Recommended workflow integration
1. Run Step 2 (`run-package`) and ensure outputs are regenerated.
2. Run `paper-tables-to-latex` to extract all manuscript tables and render page images.
3. Run this skill with the Step 2 run log — it auto-verifies numeric tables and lists any figures/visual outputs still needing manual comparison.
4. Work through the visual-review list per the section above and add verdicts to the report.
5. Use the completed verification report to populate exhibit statuses in Step 3 (`create-report`).
