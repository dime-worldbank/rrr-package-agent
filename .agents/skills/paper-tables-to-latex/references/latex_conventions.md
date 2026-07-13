# LaTeX transcription conventions

Read this before transcribing anything more complex than a plain grid of
numbers. The goal is a faithful reproduction of what the table *looks like* in
the paper — same structure, same rules, same numbers — not a redesign. When you
have a choice, pick the option that makes the LaTeX output resemble the source.

## Table of contents

1. Choosing the rule style (booktabs vs. grid)
2. Column specifications and alignment
3. Spanning cells: `\multicolumn` and `\multirow`
4. Grouped column headers
5. Numbers: decimals, ±, %, units, scientific notation, bold "best" values
6. Footnotes and table notes
7. Escaping special characters
8. Math inside cells
9. Wide, rotated, and multi-page tables
10. Fidelity rules
11. Worked examples

---

## 1. Choosing the rule style

Match what you see:

- **Horizontal rules only** (a thick line on top, a line under the header, a
  thick line at the bottom, no vertical lines) → this is the `booktabs` look.
  Use `\toprule`, `\midrule`, `\bottomrule`, and `\cmidrule(lr){2-4}` under a
  spanning header. This is the dominant style in modern papers.
- **Full grid** (boxes around every cell, vertical lines between columns) → use
  `\hline` between rows and `|` between columns in the column spec, e.g.
  `\begin{tabular}{|l|c|c|}`.
- **Mixed** → reproduce what's actually drawn; e.g. horizontal rules plus one
  vertical divider is `{l|cc}` with `\toprule/\midrule/\bottomrule`.

Never "upgrade" a grid table to booktabs or vice-versa; the point is fidelity.

## 2. Column specifications and alignment

- `l`, `c`, `r` = left / center / right. Text labels are usually `l`; numeric
  columns are usually `r` or `c`. Copy what you see.
- Cells that wrap onto multiple lines → `p{width}` (e.g. `p{3cm}`), or
  `>{\raggedright\arraybackslash}p{3cm}` for left-aligned wrapping (needs
  `array`).
- For decimal-aligned numeric columns, `siunitx`'s `S` column is ideal:
  `\begin{tabular}{l S S}` aligns on the decimal point. Optional — only reach
  for it when the source clearly aligns numbers on the decimal.

## 3. Spanning cells

- **Horizontal span** (one heading over several columns): 
  `\multicolumn{3}{c}{Header}` occupies 3 columns, centered. The number must
  equal how many columns it visually covers.
- **Vertical span** (one label down several rows): `\multirow{2}{*}{Label}`
  (needs `multirow`). Leave the covered cells in the rows below empty (just the
  `&`).
- The count of `&` plus 1 in every row must match the column count, *after*
  accounting for the width of each `\multicolumn`. This is the #1 cause of
  compile errors — check it.

## 4. Grouped column headers

Two-level headers (a group label spanning several sub-columns) are extremely
common in results tables. Pattern:

```latex
\begin{tabular}{l cc cc}
\toprule
 & \multicolumn{2}{c}{Dataset A} & \multicolumn{2}{c}{Dataset B} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
Method & Acc. & F1 & Acc. & F1 \\
\midrule
...
```

`\cmidrule(lr){2-3}` draws the short rule under just the "Dataset A" group.

## 5. Numbers

- Transcribe values **exactly**: same digits, same number of decimal places,
  same thousands separators.
- `±` → `$\pm$` (or the `\pm` symbol in a math cell). `95.2 ± 0.3` →
  `$95.2 \pm 0.3$`.
- Percent sign in data → escape it: `88.4\%`.
- Degrees → `$^\circ$`; times → `$\times$`; scientific notation
  `1.2 \times 10^{-3}` in math mode, i.e. `$1.2\times10^{-3}$`.
- **Bold best results:** if the paper bolds the best value in each column (or
  underlines the runner-up), reproduce it with `\textbf{...}` (and
  `\underline{...}`). This highlighting *is* a result — don't drop it.

## 6. Footnotes and table notes

Notes printed beneath a table (starting with `*`, `†`, or "Note:") should be
reproduced. Two easy options:

- Simple: put them after the `tabular`, in small text:
  `{\footnotesize \textit{Note:} best results in \textbf{bold}.}`
- Aligned to table width with proper superscript markers: use `threeparttable`.

```latex
\usepackage{threeparttable}
\begin{table}[htbp]\centering
\begin{threeparttable}
\caption{...}
\begin{tabular}{lcc}
\toprule
Model & Score\tnote{a} & Params \\
\midrule
... \\
\bottomrule
\end{tabular}
\begin{tablenotes}\footnotesize
\item[a] averaged over 5 seeds.
\end{tablenotes}
\end{threeparttable}
\end{table}
```

## 7. Escaping special characters

Outside math mode these characters must be escaped, or compilation breaks:

| Character | Type as |
|-----------|---------|
| `&`  | `\&`  (literal ampersand in text) |
| `%`  | `\%` |
| `$`  | `\$` |
| `#`  | `\#` |
| `_`  | `\_`  (in text; in math `_` is subscript) |
| `{` `}` | `\{` `\}` |
| `~`  | `\textasciitilde{}` |
| `^`  | `\textasciicircum{}` (in text) |
| `\`  | `\textbackslash{}` |

`&` is special because it separates columns — a stray unescaped `&` inside a
cell will throw the whole row's column count off.

## 8. Math inside cells

Wrap mathematical content in `$...$`: variables ($\alpha$, $R^2$), inequalities
($p < 0.05$), subscripts/superscripts, and symbols. Don't put plain numbers in
math mode unless they carry math (it changes spacing/font).

## 9. Wide, rotated, and multi-page tables

- **Too wide for the text block:** wrap the values in `\resizebox{\textwidth}{!}{ ... }`
  (needs `graphicx`) or use a smaller font (`{\small ...}`), matching how the
  source fits it.
- **Rotated / landscape (sideways) table:** the source is printed at 90°. Use
  `\begin{sidewaystable} ... \end{sidewaystable}` (needs `rotating`).
- **Table split across pages:** reconstruct it as one table. Add a comment
  `% spanned pages 7-8 in the source`. Only use `longtable` if the user wants a
  genuinely page-breaking table.

## 10. Fidelity rules

- Preserve row and column **order** as printed.
- Preserve **every** row, including summary rows ("Average", "Ours", totals).
- If a cell is empty or "–"/"—" in the source, keep it empty or use `--`/`---`.
- If a value is truly illegible even after re-rendering the page at 300–400 DPI,
  write your best reading and add `% TODO: verify` on that line. Do not invent
  numbers — a fabricated result is worse than a flagged uncertain one.

## 11. Worked examples

### Example A — booktabs results table with a grouped header and bold best values

What you see: a table titled "Table 2: Accuracy (%) on two benchmarks", columns
grouped under "CIFAR-10" and "CIFAR-100", each with "Top-1" and "Top-5"; the best
number in each column is bold.

```latex
\begin{table}[htbp]\centering
\caption{Accuracy (\%) on two benchmarks.}
\label{tab:2}
\begin{tabular}{l cc cc}
\toprule
 & \multicolumn{2}{c}{CIFAR-10} & \multicolumn{2}{c}{CIFAR-100} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
Method & Top-1 & Top-5 & Top-1 & Top-5 \\
\midrule
ResNet-50   & 93.1 & 99.2 & 74.5 & 92.1 \\
ViT-B       & 94.0 & 99.4 & 76.2 & 93.0 \\
Ours        & \textbf{95.3} & \textbf{99.6} & \textbf{78.1} & \textbf{93.8} \\
\bottomrule
\end{tabular}
\end{table}
```

### Example B — grid table with a vertical rule and a spanning row label

What you see: full grid, a "Setting" label spanning two rows, ± error bars.

```latex
\begin{table}[htbp]\centering
\caption{Ablation with 95\% confidence intervals.}
\label{tab:3}
\begin{tabular}{|l|c|c|}
\hline
\multirow{2}{*}{Setting} & \multicolumn{2}{c|}{Metric} \\
\cline{2-3}
 & mAP & Recall \\
\hline
Baseline      & $41.2 \pm 0.4$ & $58.0 \pm 0.6$ \\
+ module A    & $43.7 \pm 0.3$ & $60.5 \pm 0.5$ \\
+ module A\&B & $\mathbf{45.1 \pm 0.3}$ & $\mathbf{62.2 \pm 0.4}$ \\
\hline
\end{tabular}
\end{table}
```

Note `A\&B` — the ampersand inside the label is escaped so it isn't read as a
column separator.
