---
name: create-report
description: >
  Run this skill for step 3 of a PRWP reproducibility review — after running the package.
  Triggers when a reviewer says "create the report", "write the report", "draft the report",
  "step 3", "generate the verification report", "fill in the report", or "document the exhibits".
  Collects all needed information (exhibits, title, date, runtime, system specs, data handling)
  and generates a complete LaTeX reproducibility report. The template is bundled in
  assets/report_template.tex. Also works for Markdown output if preferred.
---

# Skill 3 — Create Report

## What this skill does
Collects all review information and fills in the reproducibility report.
The LaTeX template is at `assets/report_template.tex` in this skill folder.

Produces: a filled `verification_report_[PACKAGE_ID].tex` ready for Overleaf or
local LaTeX compilation.

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
- How many runs were completed? (almost always 2; 1 if runtime >48h)
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

3. **Compile** in Overleaf or locally with `pdflatex`.
   - Overleaf template: https://www.overleaf.com/2996348989fbgvwfqrxgtj#6ccc49
   - Make sure `RRR Logo.png` is in the same folder (or `graphics/` subfolder)

4. **Name the output PDF**: `reproducibility_report_[PACKAGE_ID].pdf`

---

## Markdown alternative

If the reviewer prefers Markdown (e.g. for GitHub Copilot context or quick drafts),
produce this structure instead:

```markdown
# Reproducibility Report — [PACKAGE ID]
**Paper:** [Title]
**Reviewer:** [Name]
**Date:** [Date]

---

## Main Findings
- [Overall status line]
- Code ran after: [list changes]
- Stable across [N] runs
- Runtime: ~[X] minutes

### Reproducibility Summary
- **Data:** [statement]
- **Code:** [statement]
- **Outputs:** [statement]
- **Environment:** [statement]

---

## Exhibit List

### Main Section
| Exhibit | Status | Notes |
|---------|--------|-------|
| Figure 1 | ✅ Reproduced | |
| Table 2 | ❌ Does not reproduce | Values differ for row X |

### Appendix
[Note on sampling if applicable]
| Exhibit | Status | Notes |
...

---

## Reproduction Environment
- OS: [OS]
- Processor: [Processor]
- Memory: [Memory]
- Software: [Software]
```

---

## Done with Skill 3?

- Save the compiled PDF as `reproducibility_report_[PACKAGE_ID].pdf`
- If the package **did not reproduce**: send the report to authors now (see email
  templates in Skill 1 / communication_template.md)
- If the package **reproduced**: proceed to **Skill 4 — Prepare Publication**
