---
name: prepublication-review
description: >
  Run this skill for step 5 of a PRWP reproducibility review — after Skill 4 has
  assembled the final ZIP and the metadata has been entered in the Metadata Editor,
  and BEFORE the package goes live on the Reproducible Research Repository. Triggers
  when a reviewer says "step 5", "PII check", "PII review", "check for PII",
  "pre-publication review", "final check", "check the JSON", or "is it ready to go live".
  Two parts only: Part A scans the final ZIP for personally identifiable information
  (data, code, documents, hidden files, .git history); Part B checks the Metadata
  Editor JSON export against the protocol, itself, the ZIP contents and the
  reproducibility report. Produces one short report with a single verdict.
  Bundled: scripts/scan_data.R, scripts/scan_code.py, scripts/check_metadata.py.
---

# Skill 5 — Pre-publication Review (PII + JSON consistency)

## What this skill does
The final gate before a package goes live. The package has already been verified (Skills 1–3)
and prepared (Skill 4); this is **not** another reproducibility review. Two parts:

- **Part A: PII.** Does anything in the final ZIP identify a person? Check data, code, documents
  and hidden files.
- **Part B: JSON consistency.** Is the Metadata Editor JSON correct, and does it agree with the
  protocol, with itself, with what is in the ZIP, and with the reproducibility report?

Do not review README completeness, package structure or reproducibility. Only mention a non-JSON
problem if it is PII or it makes the JSON wrong.

Produces:
1. `report/[PACKAGE_ID]/prepublication_review_[PACKAGE_ID].md` — verdict, PII line, one table of changes
2. A row in `report/prepublication_log.md`

Bundled in this skill:
- `references/PII_REVIEW.md` — Part A steps and severity scale
- `references/JSON_CHECKS.md` — Part B checklist (J1 fields, J2 datasets + data statement, J3 vs ZIP, J4 vs report)
- `assets/review_report.md` — report template
- `scripts/scan_data.R` — automated PII scan of every data file (haven / readxl / data.table)
- `scripts/scan_code.py` — automated PII scan of code, logs, notebooks, `.git` history (standard library only)
- `scripts/check_metadata.py` — automated Part B checks (standard library only; uses `pdftotext`)

**Before every review, read `references/PII_REVIEW.md`, `references/JSON_CHECKS.md` and
`assets/review_report.md` in full.**

---

## Step 1 — Gather the inputs

You need two files. If either is missing, ask the reviewer for it. Do not guess another file.

1. **The final ZIP** from Skill 4 Step 6 (`[PACKAGE_ID].zip`). Look in `package/[PACKAGE_ID]/` and
   `report/[PACKAGE_ID]/` first.
2. **The Metadata Editor JSON export** (`[PACKAGE_ID].json`, exported from the Metadata Editor after the
   reviewer entered the metadata). The draft written in Skill 4 Step 6b is only the `project_desc`
   dataset/run sections, so it will fail many J1 checks (title, producers, DataCite, tags). Use the
   full export; if the reviewer only has the draft, say which checks will be skipped.

If `report/prepublication_log.md` already has this ID, ask whether this is a re-review (new version).
If so, name the new report `prepublication_review_[PACKAGE_ID]_v2.md`.

---

## Step 2 — Set up the working folder

Review the **ZIP**, not the working package folder: the ZIP is what gets published, and things
like `.git/`, `__MACOSX/` or nested archives can be in one and not the other.

```bash
W=report/[PACKAGE_ID]/prepub
mkdir -p $W/_scans $W/unzipped
unzip -l [path/to/PACKAGE_ID.zip] > $W/_scans/zip_listing.txt
unzip -q [path/to/PACKAGE_ID.zip] -d $W/unzipped/
cp [path/to/PACKAGE_ID.json] $W/
```

The package root is the folder in `$W/unzipped/` that holds `README.pdf`.
`report/` is gitignored, so nothing here is committed.

---

## Step 3 — Run the automated checks

Run from the repo root. They give you a starting point, not a verdict.

```bash
SK=.agents/skills/prepublication-review/scripts
python $SK/check_metadata.py $W/[PACKAGE_ID].json --package "<package root>" --out $W/_scans/json_checks_auto.md
Rscript $SK/scan_data.R "<package root>" $W/_scans/data_scan.txt
python $SK/scan_code.py "<package root>" --out $W/_scans/code_scan.md
```

On Windows, if `Rscript` is not on PATH, call it by full path, e.g.
`"C:/Program Files/R/R-4.4.0/bin/Rscript.exe"`. The R scan needs `haven`, `readxl` and `data.table`.

---

## Step 4 — Manual checks

Follow `references/PII_REVIEW.md` (Part A) and `references/JSON_CHECKS.md` (Part B). Read the code,
the free text, the README, the reproducibility report and the JSON dataset notes yourself. The
scripts miss things. Re-check every FAIL/WARN by hand before reporting it.

Useful context from earlier skills (in `report/[PACKAGE_ID]/`):
- the completeness check's data classification: which files should **not** be in the ZIP
- the reproducibility report: data types, software versions, OS/hardware, run time (for J4)

---

## Step 5 — Write the report

Write `report/[PACKAGE_ID]/prepublication_review_[PACKAGE_ID].md` from `assets/review_report.md`
and add one row to `report/prepublication_log.md`
(`| ID | date | verdict | PII | reviewer |`; create the file with that header if it does not exist).

Keep it short and actionable: verdict, PII line, one table of changes. If there is no PII, the line
"No PII found" is all that is said about Part A. No summaries or lists of what was checked and passed.

### Verdict (one per package)
- **Ready to go live**: no PII and no JSON issues (or only Minor ones you list).
- **Fix JSON, then go live**: no PII; the JSON has Fix-level issues the team corrects in the Metadata Editor.
- **Hold: PII**: PII of any severity. The ZIP must change before going live.
- **Hold: data shipped**: a dataset the JSON calls restricted / limited-access / accessible / forthcoming
  is in the ZIP (not PII, but either the ZIP or the JSON must change; usually remove the file).

Then tell the reviewer the verdict and the main fixes in 3–5 lines.

---

## Step 6 — Close the loop

- **Hold: PII / Hold: data shipped** where the fix is the team's (delete a file, re-zip): go back to
  Skill 4 Step 6, rebuild the ZIP, then re-run this skill as `_v2`.
- Where the fix needs the **authors** (data or code change): draft an author email as
  `report/[PACKAGE_ID]/email_pii_[PACKAGE_ID].md` for reviewer approval. Mask the evidence in the email too.
- **Ready to go live** (or after the JSON fixes are made): the package can go live, and the reviewer can
  send the final email in Skill 4 Step 7.
- PII of High severity, or PII in Bank-produced data: escalate to the coordinator.

---

## Rules

- **Never upload, publish, push or email anything.** Work locally only.
- **Mask every piece of PII evidence** in reports, emails and chat: first letter + asterisks
  (`M***** A**`, `d******@gmail.com`, `42********`). Never paste a full value.
- Do not edit the package, the ZIP or the JSON in this skill. Write the proposed fixes in the report.
- Delete any temporary copies you extract (e.g. files pulled out of `.git`) when you finish.
  Keep `report/[PACKAGE_ID]/prepub/` until the reviewer says it can go.
- Be honest about limits. If you only sampled a file, or could not open it, and that could hide PII or
  change the verdict, add one `**Not checked:**` line under the table.
- Where `references/JSON_CHECKS.md` records a team convention (data_statement template, JEL spacing,
  accepted wording variants), the convention wins over the source
  [metadata protocol](https://github.com/worldbank/wb-reproducible-research-repository/blob/main/metadata_protocol.md).
