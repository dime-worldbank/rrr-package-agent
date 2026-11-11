---
name: run-package
description: >
  Run this skill for step 2 of a PRWP reproducibility review — after the completeness
  check passes. Triggers when a reviewer says "run the package", "set up environment",
  "step 2", "run the code", "execute the package", "check stability", or "set up stata/r/python
  environment". Guides environment setup (ado folder for Stata, renv for R,
  requirements.txt/environment.yml for Python), two full runs with Git tracking,
  stability comparison, and documents all changes needed. Outputs a run log ready to
  paste into the GitHub issue and reproducibility report.
---

# Skill 2 — Run Package

## What this skill does
Guides you through Steps 3–6 of the protocol:
- Set up a clean programming environment
- Initialize Git for change tracking
- Delete outputs and run the package from scratch
- Run a second time to verify stability
- Document everything needed for the report

Produces: a **Run Log** to paste into the GitHub issue and later into the report.

---

## Step 1 — Identify the software

Ask: **What software does this package use?**
Then jump to the relevant environment section below.

**Private data (data not in the workspace):** the reviewer runs the package on a secure
machine. Do the setup work from the code only: list the dependencies, the root path line,
the `.gitignore` below and a short run checklist. After the two runs, the reviewer runs
`.agents/skills/completeness-check/scripts/private_bundle.py postrun`, which adds to
`package/[PACKAGE_ID]/`: `data_hash_report_postrun.csv`, `hash_comparison.csv` (input vs.
generated for every data file), `code_changes.diff` (all code changes since the
`initial-package` commit), the output tables and figures, and `system_info.txt`. Use
`hash_comparison.csv` to update the completeness check, and write the Run Log from these files
plus the runtime and stability the reviewer reports. Never ask for data files or unread log files.

---

## Environment Setup — Stata

1. **Check Stata version** in the README. Note it.
2. **Create a fresh ado folder** inside the package:
   ```
   [package root]/
   └── ado/
   ```
3. At the top of the main `.do` file (or add a setup script), add:
   ```stata
   adopath + "[path to package]/ado"
   sysdir set PLUS "[path to package]/ado"
   ```
4. **Install all required packages** into this ado folder. For each package listed
   in the README (or discovered when running):
   ```stata
   net install [package], from("https://...") replace
   ```
   Or for SSC packages:
   ```stata
   ssc install [package], replace
   ```
5. **Do NOT use your personal ado folder** — all dependencies must be in the package's
   own `ado/` so they are self-contained.
6. See full instructions: https://worldbank.github.io/wb-reproducible-research-repository/resources/environment-instructions/stata.html

**Common Stata packages to watch for:** `outreg2`, `estout`, `coefplot`, `ivreg2`,
`rdrobust`, `reghdfe`, `ftools`, `gtools`, `blindschemes`, `schemepack`

---

## Environment Setup — R

1. **Check R version** in the README or `renv.lock`. Note it.
2. If the package includes `renv.lock` and `.Rprofile`:
   ```r
   # Open R in the package root, then:
   renv::restore()
   ```
3. If no `renv` setup exists, create one:
   ```r
   renv::init()
   # Install packages as needed, then:
   renv::snapshot()
   ```
4. The final package must include: `renv.lock`, `.Rprofile`, and `renv/activate.R`
5. See full instructions: https://worldbank.github.io/wb-reproducible-research-repository/resources/environment-instructions/R.html

---

## Environment Setup — Python

1. **Check Python version** in the README, `requirements.txt`, or `environment.yml`.
2. If `environment.yml` exists (conda):
   ```bash
   conda env create -f environment.yml
   conda activate [env-name]
   ```
3. If `requirements.txt` exists (pip):
   ```bash
   python -m venv myenv
   source myenv/bin/activate   # Windows: myenv\Scripts\activate
   pip install -r requirements.txt
   ```
4. If neither exists, create one after installing dependencies:
   ```bash
   pip freeze > requirements.txt
   # OR for conda:
   conda env export > environment.yml
   ```
5. See full instructions: https://worldbank.github.io/wb-reproducible-research-repository/resources/environment-instructions/python.html

---

## Step 2 — Initialize Git

Before touching anything else, set up local Git tracking with the helper in this skill
folder. Run it from the `rrr-package-agent` folder:

```bash
S=.agents/skills/run-package/scripts/track_package.py
python $S init --id [PACKAGE_ID] --raw-data [raw data folder, relative to the package]
```

This tracks the **whole** `package/[PACKAGE_ID]/` folder (one repo for Skills 2, 3 and 4),
writes the `.gitignore` below and commits `initial-package`. The history is stored in
`report/[PACKAGE_ID]/evidence/package.git`, not in the package: the package only gets a small
`.git` pointer file, so `git log` and `git diff` still work there and nothing has to be deleted
before zipping. Do not run `git init` by hand, and never delete or move that `.git` file.

**The `.gitignore` it writes (from the protocol, §2).** Git tracks code and text/image outputs
(`.csv`, `.tex`, `.txt`, `.png`, `.jpg`) so changes between runs show up as diffs. It ignores
all binary files, since Git cannot show meaningful diffs for them, and the raw data folder.
Give the raw data folder with `--raw-data` (`raw_data`, `data`, `Data/Raw`, …; repeatable).
```
## This .gitignore is for reproducibility packages to track changes in outputs only

## Binary output files - Git cannot show meaningful diffs for these
*.pdf
*.xlsx
*.xls
*.dta
*.zip
*.docx
*.doc
*.stswp
*.rar
*.7z
*.rds
*.RData
*.sav
*.parquet
*.feather
*.pkl

## Stata, R, Python and system files
*.smcl
.Rhistory
__pycache__/
*.pyc
myenv/
.DS_Store
Thumbs.db

## Ignore the raw data folder
## Note: adapt the folder name to match the package structure
/raw_data
```

> ⚠️ **This repository is LOCAL ONLY. Never push to GitHub.com.**
> The purpose is to diff outputs between runs, not to publish code.

---

## Step 3 — First Run

1. **Delete all existing outputs** before running:
   - Delete contents of output folders (tables, figures)
   - Delete intermediate/processed data files ONLY if they are generated by the code
   - **Do NOT delete** any Excel files where authors manually assembled results —
     keep those and note them in the run log
   - **Do NOT delete** the raw data files

2. **Change only the top-level directory path** in the main script. Do not make
   any other changes yet.

3. **Commit that change on its own**, then **run the package** from start to finish via the
   main script, through the helper:
   ```bash
   python $S commit --id [PACKAGE_ID] --label fix-root-path --note "main.do line 12: root path"
   python $S run --id [PACKAGE_ID] --n 1 --log main.log -- stata-mp -b do main.do
   # R: -- Rscript main.R        Python: -- python main.py        (--cwd if the script is in a subfolder)
   ```
   `run` measures the start, end and runtime, saves what the script printed and its log, writes
   a SHA-256 manifest of every file (`run1_hashes.csv`, including the binary files Git ignores)
   and commits `first-run`. All of it goes to `report/[PACKAGE_ID]/evidence/`. Use the runtime
   from `run_times.csv` in the Run Log; do not estimate it.

4. **Document every error and fix** as you go — see Run Log format below. If the run fails,
   nothing is committed: fix the cause, commit the fix on its own
   (`commit --label fix-[what] --note "[file:line, what and why]"`) and run `--n 1` again.
   One commit per fix, so each code change can be checked with `git show`.

**Common errors and fixes to document:**
- Missing package → install it, note it
- Hard-coded path → change to relative path, note it
- Missing file → check README, ask authors if unclear
- Version incompatibility → note software version, try to resolve
- `set varabbrev on/off` → add to top of main script if needed (Stata)

---

## Step 4 — Second Run (Stability Check)

> Skip this step if the first run took more than 24 hours. Note "Single run — runtime
> exceeded 24h threshold" in the run log.

1. **Delete outputs again** (same as Step 3, point 1)
2. **Run the package again** without any changes: the same `run` command with `--n 2`
   (it commits `second-run`, also when the outputs are identical).
3. **Check for differences:**
   ```bash
   python $S compare --id [PACKAGE_ID]       # run 1 vs run 2 by SHA-256, binary files included
   git -C package/[PACKAGE_ID] diff HEAD~1 HEAD -- "*.csv" "*.txt" "*.tex"   # what changed, for text outputs
   ```
   `compare` writes `evidence/run_comparison.csv`. Or in GitHub Desktop: compare the two commits visually.

**Interpreting differences:**
| File type | Change | Verdict |
|-----------|--------|---------|
| `.csv`, `.txt`, `.tex` | Values changed | ❌ UNSTABLE — investigate |
| `.csv`, `.txt`, `.tex` | No change | ✅ Stable |
| `.png`, `.jpg` | File changed | `compare` already checked the checksums; open the image only if they differ — may be metadata only |
| `.dta`, `.xlsx` | Changed | ⚠️ May be timestamps — not necessarily unstable |
| `.dta`, `.xlsx` | No change | ✅ Stable |

**If outputs are unstable:**
- For Stata: run `reprun` to locate where divergence starts
  ```stata
  reprun "[main_do_file].do"
  ```
- For R/Python: check for random seeds — add `set.seed()` / `random.seed()` if missing
- Document the discrepancy and discuss with coordinator before returning to authors

---

## Step 5 — Record System Information

Fill in your computer specs (needed for the report):

```
Operating System: _______________  (e.g. Windows 11 Enterprise)
Processor:        _______________  (e.g. Intel Core i5-1145G7 @ 2.60GHz)
Memory:           _______________  (e.g. 15.7 GB)
Software:         _______________  (e.g. Stata 18.0 MP / R 4.3.1 / Python 3.11.5)
Runtime (run 1):  _______________  (e.g. ~45 minutes)
Stability:        _______________  (Stable across 2 runs / Unstable — see notes)
```

---

## Step 6 — Send Confirmation Email to Authors

Once the package runs (even if with minor fixes), draft this email for the reviewer to send,
saved as `report/[PACKAGE_ID]/emails/2_run_confirmation.md`:

```
Dear [Author Name],

I hope this message finds you well. My name is [Your Name], and I am a
member of the PRWP Reproducibility Verification team. We have received
the reproducibility package for your paper "[Paper Title]." We were able
to run the code after making the following adjustments:

- [one bullet per change, from "Changes made to code" in the Run Log]

[If no change was needed, replace the last sentence and the list with:
"We were able to run the code without any changes."]

We are now moving forward with the verification and aim to share the
results by [date 2 weeks from today, e.g. November 25, 2026]. You will
receive a detailed reproducibility report and, if all criteria are met,
your package will be published in our Reproducible Research Repository
(https://reproducibility.worldbank.org/).

If you have any questions, please don't hesitate to contact us.

Best regards,
[Your Name]
PRWP Reproducibility Verification Team
reproducibility@worldbank.org
```

---

## Run Log (output of this skill)

Produce this at the end. Paste into the GitHub issue.

```
RUN LOG — [PACKAGE ID]
Date of run: [date]
Reviewer: [name]
==========================================

ENVIRONMENT
  Software: [e.g. Stata 18.0 MP]
  OS: [e.g. Windows 11 Enterprise]
  Processor: [e.g. Intel i5-1145G7 @ 2.60GHz]
  Memory: [e.g. 15.7 GB]

DEPENDENCIES INSTALLED
  - [package name] (SSC / net install / pip / CRAN)
  - [package name]

CHANGES MADE TO CODE
  1. [e.g. Changed root path in main.do line 12]
  2. [e.g. Added `set varabbrev on` to top of main.do]
  3. [e.g. Installed outreg2 to ado/ folder]

RUNTIME
  Run 1: ~[X] minutes/hours
  Run 2: ~[X] minutes/hours (or: SKIPPED — runtime >24h)

STABILITY
  ✅ Stable — no differences in .csv/.txt/.png outputs between runs
  ❌ Unstable — [describe differences]

NOTES
  [Any other observations]

NEXT STEP: Skill 3 — Create Report
```

---

## Done with Skill 2?

- Save the Run Log as `report/[PACKAGE_ID]/run_log.md` and paste it into the **GitHub issue**
  (commit: `second-run` or `first-run`)
- Run `python $S changes --id [PACKAGE_ID]` to write `evidence/AI_CHANGES.md`: every code change
  with its commit and file:line, for the reviewer to check
- Move to **Skill 3 — Create Report**
