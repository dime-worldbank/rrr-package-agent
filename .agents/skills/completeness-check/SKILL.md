---
name: completeness-check
description: >
  Run this skill at the START of every PRWP reproducibility review — step 1 of the
  workflow. Triggers whenever a reviewer says "check the package", "verify completeness",
  "step 1", "start the review", "is the package complete", or receives a new submission.
  Walks through the full completeness checklist: manuscript, README, data availability
  statement, raw vs processed data, and flags any Bank-produced datasets that need
  Microdata Library archiving. Outputs a structured checklist report and a ready-to-send
  author email if items are missing.
---

# Skill 1 — Completeness Check

## What this skill does
Guides you through the Step 2a/2b completeness and data access verification for a
reproducibility package. Produces:
1. A filled checklist with pass/fail for each item
2. A flagged list of issues (missing elements, data concerns)
3. A draft author email if anything is missing

---

## How to use this skill

Ask the reviewer to share the package location (local path, SharePoint link, or
describe what they can see). Then work through each section below in order.

---

## Section A — Core Package Components

Check each item. Mark ✅ PRESENT or ❌ MISSING.

### A1. Manuscript
- Is a manuscript (PDF or Word doc) included, OR is there a link to the published paper?
- **Why it matters**: Without the manuscript, you cannot compare code outputs to paper exhibits.
- **If missing**: Flag for author email — this is a hard blocker.

### A2. README file
Check the README covers ALL of the following. Each sub-item can be ✅ or ❌:

- [ ] **Software and version** (e.g., "Stata 18.0 MP", "R 4.3.1", "Python 3.11"); not a blocker since replicator will run it in their own environment, but important for troubleshooting
- [ ] **How to run** — which file to execute first, order of scripts if no main file
- [ ] **Top-level directory line** — which line in the main script to change for a new machine, not a blocker but helpful for replicators, not needed to communicate to authors if there is a main script. 
- [ ] **Output mapping** — table/figure → script that generates it (or reference to a linkage table)
- [ ] **Data Availability Statement** (can be in README or separate file) — see Section B

A README with none of these AND no data info → **return to authors immediately**.
A README missing some items → note issues, proceed with review, include in author email.

### A3. Code
- [ ] Code files that go from raw data all the way to paper exhibits
- [ ] A main script (one-button run) — OR — README specifies exact execution order
- [ ] No unnecessary code (e.g., exploratory scripts, old versions) — note but don't block

### A4. Data
- [ ] Raw data files are present (for verification purposes)
- [ ] Data looks **unprocessed** — see Section C for how to assess this
- [ ] If data is restricted/private: README explains how to access it

### A5. Outputs
- [ ] Raw outputs (tables as .txt/.csv/.tex, figures as .png/.pdf) are present
- [ ] If outputs are missing: note it, but don't block the review

---

## Section B — Data Availability Statement

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

## Section E — Generate Checklist Report

After working through Sections A–D, produce a structured report in this format:

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

---

## Section F — Author Email (if items are missing)

If anything is missing, draft an email using the relevant boilerplate below.
Mix and match sections as needed.

**Opening:**
```
Dear [Author Name],

Thank you for submitting your reproducibility package for "[Paper Title]."
Upon initial review, we found some items that need to be addressed before
we can proceed with verification.
```

**For missing README / data statement:**
```
The current package lacks a complete data availability statement. For each
dataset, please provide: (1) dataset name, (2) date accessed, (3) URL if
publicly available, or step-by-step access instructions if restricted,
and (4) a statement confirming you had legitimate access to all data.
See [this example README](https://reproducibility.worldbank.org/index.php/catalog/98)
for reference.
```

**For missing manuscript:**
```
Please include the final manuscript that will be used for publication —
this is the version we compare exhibits against during verification.
```

**For missing raw data / processed data flag:**
```
We noticed that [filename] may be a processed dataset rather than the
original raw data. Complete reproducibility requires starting from
undprocessed data. Could you confirm whether raw source data and the
construction code are available?
```

**For Microdata Library:**
```
The dataset [filename] appears to be original data collected by your team.
Per World Bank policy, this dataset should be archived in the Microdata
Library (https://microdata.worldbank.org/). We have copied this message
to microdata@worldbank.org for coordination.
```

**Closing:**
```
You can update directly the folder shared with us, and let us know once these items have been
addressed. Feel free to reach out with any questions.

Best regards,
[Your Name]
PRWP Reproducibility Verification Team
reproducibility@worldbank.org
```

---

## Done with Skill 1?

Once the checklist is complete and any author emails are drafted:
- Paste the checklist report into the **GitHub issue**
- If proceeding: move to **Skill 2 — Run Package**
- If returning to authors: update GitHub issue status and wait for resubmission
