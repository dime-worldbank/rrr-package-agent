---
name: create-report
description: >
  Run this skill for step 3 of a PRWP reproducibility review — after running the package.
  Triggers when a reviewer says "create the report", "write the report", "draft the report",
  "step 3", "generate the verification report", "fill in the report", or "document the exhibits".
  Collects all needed information (exhibits, title, date, runtime, system specs, data handling)
  and generates the reproducibility report in two formats: Markdown (.md, the working
  version) and LaTeX (.tex, from assets/report_template.tex).
---

# Skill 3 — Create Report

## What this skill does
Collects all review information and fills in the reproducibility report.
The LaTeX template is at `assets/report_template.tex` in this skill folder.

Produces, in `report/[PACKAGE_ID]/`:
- `verification_report_[PACKAGE_ID].md` — the main version, reviewed in VS Code and
  exported to PDF (see **Markdown report format** below)
- `verification_report_[PACKAGE_ID].tex` — the same content filled into the LaTeX
  template, for Overleaf or local compilation (kept for now, alongside the .md)

Both files must have the same sections, wording and exhibit statuses.

---

## Information to collect before generating the report

Work through these questions with the reviewer. Many answers come from the Run Log
produced in Skill 2.

### 1. Basic Info
- **Package ID** (e.g. `RR_KEN_2026_585`)
- **Paper title** (full title as it appears in the manuscript)
- **Reviewer name**
- **Today's date**
- **Manuscript version used** — was it a shared draft by email, or the published paper?
  (e.g. "the paper shared by the authors by email on March 3rd" or "the published paper")

### 2. Overall Outcome
Ask: **Did every exhibit reproduce?**

Choose one:
- ✅ **Fully reproduced** (main section only) →
  `\textcolor{OliveGreen}{\textbf{Every exhibit in the main section of the paper has been reproduced accurately.}}`
- ✅ **Fully reproduced** (main + appendix sample) →
  `\textcolor{OliveGreen}{\textbf{Every exhibit in the main section of the paper and 10 randomly selected exhibits in the appendix were reproduced accurately.}}`
- ❌ **Did not reproduce** →
  `\textcolor{Red}{\textbf{The exhibits in the paper did not meet the requirements for computational reproducibility, with X exhibits failing to reproduce accurately.}}`

### 3. Run Steps (changes made)
From the Run Log — list every change made to get the code running.
Example:
```latex
\item Adjusted the root file path in \texttt{main.do}, line 12.
\item Installed the \texttt{outreg2} package to the \texttt{ado/} folder.
```
If no changes were needed: `\item No modifications were required.`

### 4. Runtime and Stability
- How long did the package take to run? (e.g. "~45 minutes", "~3 hours")
- How many runs were completed? (almost always 2; 1 if runtime >24h)
- Was the output stable? (Yes / No — if No, describe)

### 5. System Specifications
From the Run Log:
- OS (e.g. "Windows 11 Enterprise")
- Processor (e.g. "Intel(R) Core(TM) i5-1145G7 CPU @ 2.60GHz")
- Memory (e.g. "15.7 GB")
- Software version (e.g. "Stata 18.0 MP")

### 6. Data Handling (Verification Process section)
This summarizes how the review treated different data types. Ask:

- **What types of data were in the package?** (open/public, accessible-but-no-redistribution,
  limited-access, restricted, forthcoming)
- **Was restricted data provided directly by authors for verification?**
- **Was a comparison report created?** (for accessible/limited-access data)
- **Was a data hash report created?**

Use the appropriate boilerplate:

**Open data only:**
```latex
\item All data used in this package is publicly available and included in the
reproducibility package.
\item \textit{data\_hash\_report.csv} lists the SHA256 hashes of all files in
the Data folder to support data integrity checks.
```

**Mixed data (open + restricted):**
```latex
\item The reproducibility package relies on [X] types of data: [list them].
\item Open data is included in the public reproducibility package.
\item Reviewers used [forthcoming/restricted] data provided directly by the authors
to conduct the reproducibility verification; this data is not included in the public package.
[The data is forthcoming on the World Bank Microdata Library. / Access instructions are in the README.]
\item \textit{data\_hash\_report.csv} lists the SHA256 hashes of all files in the Data
folder to support data integrity checks. Users who acquire the data can use this file
to verify it has not been altered.
```

**With comparison report:**
```latex
\item Reviewers verified that the [accessible/limited-access] data matches what was
provided by the authors; results of this verification are documented in
\textit{comparison\_report.csv}.
```

### 7. Reproducibility Summary Lines
Four standard lines — fill in the correct option for each:

**Data:**
Choose the most restrictive that applies:
- `All data sources are publicly available and included in the reproducibility package.`
- `All data sources are publicly available but not all are included in the reproducibility package.`
- `Some data is restricted and has not been included in the reproducibility package. For more details, refer to the README file.`
- `All data is restricted and has not been included in the reproducibility package. For more details, refer to the README file.`
- `Some/All data is forthcoming in the World Bank Microdata Library.`

**Code:**
- `All code files (from cleaning to analysis) are included in the reproducibility package.`
- (or note if any code is missing)

**Outputs:**
- `All outputs are generated by code included in the reproducibility package.`
- (or note if any outputs are manually produced)

**Dependencies:**
- `The reviewers created a new environment using the latest versions of dependencies available at the moment of the review.`
- (or: `The reviewers used the environment specified in renv.lock / environment.yml.`)

---

## Exhibit List — the most important section

### How to build the exhibit list

For **each** table and figure in the paper (main section), determine its status.
Compare the numbers first: tables from their `.csv`/`.tex`/`.txt` outputs, figures from the
data files behind them, and image files by checksum (`shasum`). Open an image only when the
checksums differ or no data file exists, and open each image once.
If the appendix has more than 10 exhibits, note which 10 were randomly selected
(see randomization code link in protocol).

**Status options and LaTeX color codes:**

| Status | Color | When to use |
|--------|-------|-------------|
| Reproduced | `\textcolor{OliveGreen}{Reproduced.}` | Values match exactly; code generated the output |
| Manual changes | `\textcolor{LimeGreen}{Reproduced (manual changes).}` | Values match but required Excel or copy-paste step |
| Values only | `\textcolor{Goldenrod}{All values reproduced.}` | Underlying numbers match but figure not in outputs |
| Cannot verify | `\textcolor{BurntOrange}{Could not be verified.}` | Output not found or cannot be traced to code |
| Does not reproduce | `\textcolor{Red}{Does not reproduce.}` | Values differ; always explain the difference |
| Does not apply | `\textcolor{Gray}{Does not apply.}` | Not an analytical output (e.g. variable definitions table) |

**Format for each exhibit:**
```latex
\item \textbf{Figure 1} \textcolor{OliveGreen}{Reproduced.}

\item \textbf{Table 2} \textcolor{Red}{Does not reproduce.} [Describe the discrepancy.
  For numeric differences, show a small comparison table. For figures, reference
  screenshots named Figure2_paper.png and Figure2_code.png.]
```

**For "does not reproduce" items**, include a side-by-side comparison table:
```latex
\item \textbf{Table A.14} \textcolor{Red}{Does not reproduce.}
There is a discrepancy in the coefficient for [variable]. See below:

\begin{table}[h]
\centering
\begin{tabular}{cc}
\begin{minipage}{.5\linewidth}
\centering
\textbf{Code} \\
\includegraphics[width=.9\linewidth]{TableA14_code.png}
\end{minipage}
\begin{minipage}{.5\linewidth}
\centering
\textbf{Paper} \\
\includegraphics[width=.9\linewidth]{TableA14_paper.png}
\end{minipage}
\end{tabular}
\end{table}
```

In the Markdown version the same comparison is an HTML table:
```html
<table>
<tr><th>Code</th><th>Paper</th></tr>
<tr>
<td><img src="graphics/Figure2_code.png" width="100%"></td>
<td><img src="graphics/Figure2_paper.png" width="100%"></td>
</tr>
</table>
```

### Making the comparison screenshots

Every exhibit marked **Does not reproduce** gets a Code / Paper pair, in both the .md and
the .tex. This is required, also when running headless: make the images yourself with the
commands below, never ask the reviewer for screenshots and never reference an image that
does not exist. Save them in `report/[PACKAGE_ID]/graphics/` as `[Exhibit]_code.png` and
`[Exhibit]_paper.png`, with no spaces or dots in `[Exhibit]` (e.g. `FigureB2`, `TableA14`).

**Paper side**: crop the exhibit from the manuscript PDF.
1. Find its page: `pdftotext -layout manuscript.pdf - | grep -n "Figure 2"`, or loop over pages
   with `pdftotext -f P -l P`. Use the page with the caption *and* the exhibit body, not the
   first page that mentions it in the text.
2. Render that page: `pdftoppm -png -r 150 -f P -l P -singlefile manuscript.pdf graphics/Figure2_page`
3. Crop to the exhibit (caption + figure/table + notes) with Pillow:
   `python3 -c "from PIL import Image; Image.open('graphics/Figure2_page.png').crop((x0,y0,x1,y1)).save('graphics/Figure2_paper.png')"`.
   Get the coordinates from `pdftotext -bbox-layout -f P -l P` (points × 150/72 = pixels)
   or by opening the page image once. Delete the `_page.png` afterwards. If cropping fails,
   use the full page; a full page is better than no image.

**Code side**: the output the package produced in the run.
- `.png`/`.jpg`: copy it. `.pdf`: `pdftoppm -png -r 150 -singlefile out.pdf graphics/Figure2_code`.
  `.eps`/`.svg`/`.gph` or other: convert with `sips -s format png` (macOS), `rsvg-convert`,
  or the package's own software (e.g. Stata `graph export`, R `ggsave`), whichever is installed.
- Tables: a small Code vs Paper table of the cells that differ is enough (numbers copied
  from the output file). Add the screenshot pair only when the layout itself differs
  (missing rows/columns); then render the output to PNG or crop it from a PDF the
  package produced.
- If the code produced no file for the exhibit, the status is **Could not be verified**,
  not Does not reproduce, and no pair is needed.

Open each finished pair once to check that the crop shows the right exhibit and the
difference is visible, then describe the difference in one or two sentences under it
(e.g. "The confidence bands in the code output are wider after 2015.").

**Appendix note** (if >10 exhibits, sampled):
```latex
For the Appendix, we did not review every exhibit. Instead, we randomly selected
10 exhibits to assess. Since they were chosen randomly, we assume that if all
selected exhibits are reproducible, the rest should be as well. The seed used was
[SEED], the Stata version was [VERSION], and the exhibits selected were: X, X, X.
```
If all appendix exhibits were reviewed: `All appendix exhibits were reviewed.`

---

## Generate the report

Once you have all the information above, do the following:

1. **Copy** `assets/report_template.tex` (in this skill folder) to the reviewer's
   working directory and rename it `verification_report_[PACKAGE_ID].tex`

2. **Replace every `%%PLACEHOLDER%%`** with the collected information:

| Placeholder | Replace with |
|-------------|-------------|
| `%%PAPER_TITLE%%` | Full paper title |
| `%%PACKAGE_ID%%` | e.g. `RR\_KEN\_2026\_585` (escape underscores) |
| `%%REVIEWER_NAME%%` | Reviewer's name |
| `%%DATE%%` | Today's date |
| `%%OVERALL_STATUS_LINE%%` | The `\textcolor{...}` line from Section 2 above |
| `%%RUN_STEPS%%` | `\item ...` lines from Section 3 |
| `%%STABILITY_RUNS%%` | `2` or `1` |
| `%%RUNTIME%%` | e.g. `\sim45` minutes |
| `%%MANUSCRIPT_VERSION%%` | e.g. `paper shared by email on March 3rd` |
| `%%DATA_HANDLING%%` | `\item ...` lines from Section 6 |
| `%%DATA_STATEMENT%%` | From Section 7 |
| `%%CODE_STATEMENT%%` | From Section 7 |
| `%%OUTPUTS_STATEMENT%%` | From Section 7 |
| `%%ENV_STATEMENT%%` | From Section 7 |
| `%%MAIN_EXHIBITS%%` | `\item \textbf{...}` lines |
| `%%APPENDIX_NOTE%%` | Appendix sampling note or empty |
| `%%APPENDIX_EXHIBITS%%` | `\item \textbf{...}` lines or empty |
| `%%OS%%` | e.g. `Windows 11 Enterprise` |
| `%%PROCESSOR%%` | e.g. `Intel(R) Core(TM) i5-1145G7 @ 2.60GHz` |
| `%%MEMORY%%` | e.g. `15.7 GB` |
| `%%SOFTWARE%%` | e.g. `Stata 18.0 MP` |

3. **Write the Markdown version** following **Markdown report format** below.

4. **Compile** in Overleaf or locally with `pdflatex`.
   - Overleaf template: https://www.overleaf.com/2996348989fbgvwfqrxgtj#6ccc49
   - Make sure `RRR Logo.png` is in the same folder (or `graphics/` subfolder)

5. **Name the output PDF**: `reproducibility_report_[PACKAGE_ID].pdf`

---

## Markdown report format

Always produce the `.md` alongside the `.tex`. It should look as close as possible to
the compiled LaTeX PDF. Reference example: `report/RR_WLD_2026_806/verification_report_RR_WLD_2026_806.md`.

Rules:
- **Logo**: copy `assets/RRR Logo.png` to `report/[PACKAGE_ID]/graphics/` and reference it
  as `graphics/RRR%20Logo.png`.
- **Body text and links are black.** Only exhibit statuses and the overall status line
  are colored. Do not use plain Markdown links (`[text](#x)`) — previews show them in a
  link color. Use `<a href="#x" style="color:inherit;text-decoration:none">…</a>` so they
  render like body text but stay clickable.
- **Internal links** (like `
ameref` in the .tex): put an explicit anchor
  `<a id="..."></a>` on its own line before each section heading, using the same ids as
  the .tex labels: `main-findings`, `output-list`, `reproduction-environment`. The
  Contents list and any cross-reference ("see Section 2") link to these ids.
- **Status colors** (inline `<span style="color:...">`):

| Status | LaTeX color | Hex |
|--------|-------------|-----|
| Reproduced. | OliveGreen | `#3C8031` |
| Reproduced (manual changes). | LimeGreen | `#8DC73E` |
| All values reproduced. | Goldenrod | `#FFDF42` |
| Could not be verified. | BurntOrange | `#F7921D` |
| Does not reproduce. | Red | `#ED1B23` |
| Does not apply. | Gray | `#949698` |

- Exhibits are bullet lists (as in the .tex), not tables.
- For "does not reproduce" comparisons, show Code and Paper screenshots side by side
  with an HTML `<table>` of two `<img>` cells (images in `graphics/`).

Skeleton:

```markdown
<div align="center">

<img src="graphics/RRR%20Logo.png" alt="Reproducible Research Repository" width="70%">

<h1><em>[Paper title]</em></h1>

<h3><em>First Submission: [PACKAGE_ID]<br>[Reviewer name]<br>reproducibility@worldbank.org</em></h3>

<h3><em>[Date]</em></h3>

</div>

This review verifies the reproducibility of the exhibits included in the paper *"[Paper title]"*.

**Contents in this review**:

1. <a href="#main-findings" style="color:inherit;text-decoration:none">Main findings</a>
2. <a href="#output-list" style="color:inherit;text-decoration:none">List of exhibits and reproducibility status</a>
3. <a href="#reproduction-environment" style="color:inherit;text-decoration:none">Reproduction Environment</a>

<a id="main-findings"></a>

## 1 Main findings

<span style="color:#3C8031"><strong>[Overall status line]</strong></span>

- The code was successfully executed on a new computer after:
  1. [Run step]

- The output demonstrates consistent stability across multiple runs. Specifically, executing the code [N] times consecutively yielded identical results.

- The code takes approximately [runtime] to run.

- We conducted our reproducibility analysis based on the [manuscript version].

- **Verification Process and Data Handling**:
  - [Data handling lines]

- **Reproducibility Summary**:
  - **Data**: [statement]
  - **Code**: [statement]
  - **Outputs**: [statement]
  - **Dependencies environment**: [statement]

<a id="output-list"></a>

## 2 List of exhibits and reproducibility status

**Results in the Main Section of the Paper**

- **Table 1** <span style="color:#3C8031">Reproduced.</span>
- **Figure 2** <span style="color:#ED1B23">Does not reproduce.</span> [Explain differences.]

<br>

**Results in the Annex**

[Appendix note]

- **Table A1** <span style="color:#3C8031">Reproduced.</span>

<a id="reproduction-environment"></a>

## 3 Reproduction Environment

Paper exhibits were reproduced on a computer with the following specifications:

- OS: [OS]
- Processor: [Processor]
- Memory available: [Memory]
- Software version: [Software]
```

**Export the .md to PDF** (run it yourself, don't ask the reviewer to print from the preview):

```
python .agents/skills/create-report/scripts/md_to_pdf.py report/[PACKAGE_ID]/verification_report_[PACKAGE_ID].md
```

This writes `report/[PACKAGE_ID]/reproducibility_report_[PACKAGE_ID].pdf` using headless
Chrome/Edge. The Contents links stay clickable, and YAML front matter is ignored. If the
PDF is open in a viewer the script stops; ask the reviewer to close it and rerun.
Check the layout once afterwards: run `pdfinfo` for the page count and `pdftotext -layout`
for the text, and open only the pages with figures or tables as images (Read with `pages`),
one time each.

---

## Done with Skill 3?

- Save the compiled PDF as `reproducibility_report_[PACKAGE_ID].pdf`
- If the package **did not reproduce**: draft the email that sends the report to the authors as
  `report/[PACKAGE_ID]/emails/3_report_to_authors.md`, for the reviewer to send now, from this
  template. One bullet per exhibit that does not reproduce or could not be verified, each in
  one plain sentence; the detail stays in the report.

  ```
  Dear [Author Name],

  I hope you are well. I am writing to share our reproducibility review of
  your paper, "[Paper Title]."

  We found that the paper is not fully reproducible with the package
  provided. Here is a summary of our findings:

  - [Exhibit: what differs between the paper and the code output]

  You will find more details in the attached report.

  I am happy to set up a call to discuss the findings or answer any questions.

  We appreciate your commitment to reproducible research and look forward
  to your resubmission.

  Best regards,
  [Your Name]
  PRWP Reproducibility Verification Team
  reproducibility@worldbank.org
  ```
- If the package **reproduced**: proceed to **Skill 4 — Prepare Publication**
