---
name: completeness-check
description: >
  This skill verifies the completeness of a reproducibility package and its documentation as submitted by authors to the reproducibility verification team. Run this skill whenever a reviewer says "check the package", "verify completeness", "is the package complete".
---

## Expected outputs of this skill
1. A filled checklist with pass/fail for each item
2. A flagged list of issues (missing elements, data concerns)
3. A draft author email if anything is missing

Folder paths without `./`, such as `report/` and `package/` are relative to the root of this repository. Files with `./` are relative to the skill folder with this SKILL.md file.

---

## Step 0 — Setup

Then start by copying the file `./assets/completeness_template.json` into the `report/` folder renaming it to `completeness_check_<package-id>.json`. This will be your working file for this skill.

Start by finding the package readme in the `package/<package-id>/` folder. If you find multiple README files in the package folder, choose the one that appears most complete or relevant by inspecting its content or by selecting the one closest to the package root `package/<package-id>/`.

After finding the readme, update the `readme` section in the `report/completeness_check_<package-id>.json` file.

---

## Section A — Core Package Components

### Step 1. Manuscript
- Is a manuscript (PDF or Word doc) included in the package, OR is there a link to the published paper in the readme?

Update the `manuscript` section in the `report/completeness_check_<package-id>.json` with this information.

---

### Step 2. README file

- **Software and version** (e.g., "Stata 18.0 MP", "R 4.3.1", "Python 3.11"); not a blocker since replicator will run it in their own environment, but important for troubleshooting

Update the `software` section in the `report/completeness_check_<package-id>.json` with this information.

---

### Step 3. Code
- **How to run** — instructions on how to run the code. For example a one-button run main script that runs all other scriots, or a detailed description of what order the code files in the folder. The main script is not the final script, but a script that allows the full package to be run by running a single file.
- **Root directory** — which line in the main script to change for a new machine
- **Relevant code files** - by just looking at the names of the code files, to your best ability, determine whether::
  - All code files that go from raw data all the way to paper exhibits seems to be included
  - No obviously unnecessary code (e.g., exploratory scripts, old versions) are included. This is a judgment call, but if there are many code files and it's not clear which ones are relevant, note this as a potential issue.

Update the `code` section in the `report/completeness_check_<package-id>.json` with this information.

---

## Step 4 - Data Documentation

### Data Availability Statement

Start by looking for a data availability statement in the README. For each input data mentioined in the README, copy the `./assets/data_template.json` file into the `data` list section of the `report/completeness_check_<package-id>.json` file. And then fill it out accodingly:

- [ ] **Data Availability Statement** (can be in README or separate file) — see Section B
- [ ] Raw data files are present in package
- [ ] Data looks **unprocessed** — see Section C for how to assess this
- [ ] If data is restricted/private: README explains how to access it

The Data Availability Statement (DAS) can be in the README or a separate file.
Check each dataset mentioned:

For **each dataset**, verify these four fields exist:
1. **Dataset name** (descriptive, e.g. "World Development Indicators")
2. **Date accessed** (month-year is sufficient, e.g. "June 2024")
3. **URL** — if publicly available, a direct download link
4. **Access instructions** — if restricted, how a third party would get access

Also check:
- [ ] **Rights statement** — authors confirm they had legitimate access to all data
  (e.g. "The authors had permission to use all datasets listed above.")

---

## Section C — Raw vs. Processed Data Assessment

This is a judgment call. Use these signals:

**Signals that data IS raw (good):**
- File names like `hh_survey_raw.dta`, `WDI_download_2024.csv`
- README says "downloaded from [URL] on [date]"
- File contains more variables than used in analysis
- Presence of a cleaning/processing script that reads this file

**Signals that data may be PROCESSED (flag for review):**
- File names like `analysis_data.dta`, `final_dataset.csv`, `merged_hh_firm.dta`
- Only the exact variables used in regressions are present
- No cleaning script is present, but a "data" folder exists
- Variable labels reference constructed or derived variables

**If data appears processed:**
> Flag: "The file `[filename]` appears to be a processed/intermediate dataset rather
> than raw data. Please confirm: (1) is this the original data as downloaded, or was
> it constructed from other sources? (2) If constructed, are the source datasets and
> construction code included?"

---

## Section D — Bank-Produced Data → Microdata Library Flag

Scan the README and data folder for datasets that appear to be **produced by the
World Bank team** (survey data, administrative data collected by the project,
experimental data from an RCT, etc.).

**Signals this is Bank-produced data:**
- README says "data collected by the authors", "household survey conducted by..."
- Files named with the project name, country, and year suggesting original collection
- Survey instruments or questionnaires are included in the package
- Variables include respondent IDs, GPS coordinates, consent indicators

**If Bank-produced data is found:**
Flag it clearly:
> ⚠️ MICRODATA LIBRARY FLAG: The dataset `[filename]` appears to be original data
> produced by the World Bank team. Per policy, this must be archived in the
> [World Bank Microdata Library](https://microdata.worldbank.org/) before or
> concurrent with publication of the reproducibility package. Note this in the
> GitHub issue and include in the author communication.

--- 

## Step 5 - Outputs
- [ ] **Output mapping** — table/figure → script that generates it (or reference to a linkage table)
- [ ] Raw outputs (tables as .txt/.csv/.tex, figures as .png/.pdf) are present
- [ ] If outputs are missing: note it, but don't block the review

---

## Section E — Generate Checklist Report

After working through Sections A–D, use the `report/completeness_check_<package-id>.json` file to generate a structured report. To indicate present or missing, use ✅ PRESENT or ❌ MISSING.

```
COMPLETENESS CHECK — [PACKAGE ID]
Date: [today]
Reviewer: [name]
==========================================

CORE COMPONENTS
  ✅ Manuscript: [title or "link provided"]
  ✅ README: Present
     ❌ Missing: software version, output mapping
  ✅ Code: Present, main script found (main.do)
  ✅ Data: Present
     ⚠️  [filename] may be processed — see note below
  ❌ Outputs: Not present — noted, proceeding

DATA AVAILABILITY STATEMENT
  ✅ Dataset 1: "WDI" — name ✅ date ✅ URL ✅ instructions N/A
  ❌ Dataset 2: "Household Survey" — name ✅ date ❌ URL ❌ instructions ❌
  ❌ Rights statement: Missing

DATA FLAGS
  ⚠️  analysis_data.dta — appears processed, not raw
  ⚠️  MICRODATA LIBRARY: hh_survey_endline.dta appears Bank-produced

VERDICT
  [ ] PROCEED — package is complete enough to run
  [ ] RETURN TO AUTHORS — [list hard blockers]

NOTES FOR GITHUB ISSUE
  [paste any notes here]
```

A README with none of these AND no data info → **return to authors immediately**.
A README missing some items → note issues, proceed with review, include in author email

---

## Section F — Author Email (if items are missing)

If anything is missing, draft an email using the template in `assets/author_email_draft_template.md`. First, copy this file into the `root/report/` folder and then read the <Instructions> in the template and customize the email based on the specific issues you found. Do not attempt to send the email. Confirm this by returning a file path to the draft email to the user.

---

## Final checklist

Before concluding, ensure you have:
- Created a report in the `report/` folder summarizing your findings
- Created a draft author email if there are any missing items or concerns



