---
name: prepare-publication
description: >
  Run this skill for step 4 of a PRWP reproducibility review — after the report is
  complete and exhibits have been verified. Triggers when a reviewer says "prepare
  the package", "publication prep", "step 4", "zip the package", "add the license",
  "create the hash report", "prepare for publication", "publish the package", or
  "finalize the package". Guides adding the BSD3 license, converting README to PDF,
  generating the data hash report, assembling the final ZIP structure, and preparing
  metadata. Bundled assets: LICENSE_template.txt, generate_data_hash_report.py.
---

# Skill 4 — Prepare Publication

## What this skill does
Assembles the final reproducibility package for publication on
[reproducibility.worldbank.org](https://reproducibility.worldbank.org/).

Produces:
1. `LICENSE.txt` (Modified BSD3, year updated)
2. `README.pdf` (converted from README if not already PDF)
3. `data_hash_report.csv` (SHA-256 hashes of all data files)
4. `[PACKAGE_ID].zip` with correct internal structure
5. A metadata checklist ready for the Metadata Editor

Assets bundled in this skill:
- `assets/LICENSE_template.txt` — the BSD3 license text
- `assets/generate_data_hash_report.py` — script to hash data files

---

## Step 1 — Add LICENSE.txt

1. Open `assets/LICENSE_template.txt` from this skill folder.
2. Replace `%%YEAR%%` with the current year.
3. Save as `LICENSE.txt` at the **top level** of the reproducibility package folder.

The license text starts with:
```
Copyright [YEAR], World Bank
```
followed by the full Modified BSD3 text. Reference URL for the license:
https://opensource.org/license/bsd-3-clause/

---

## Step 2 — Convert README to PDF

The README **must** be in PDF format in the final package.

- If the README is already a PDF: rename to `README.pdf` if not already named that.
- If the README is Markdown (`.md`): convert to PDF using:
  - **Pandoc** (recommended): `pandoc README.md -o README.pdf`
  - **VS Code**: use the Markdown PDF extension
  - **Online**: paste into a Markdown-to-PDF converter
- If the README is a Word doc (`.docx`): save/export as PDF, name it `README.pdf`
- Remove any non-PDF versions of the README from the package root (keep only `README.pdf`)

---

## Step 3 — Generate Data Hash Report

The data hash report creates SHA-256 fingerprints for all data files, allowing
future users to verify data integrity.

**Option A — Use the bundled Python script (recommended):**

1. Copy `assets/generate_data_hash_report.py` to the **root** of the reproducibility
   package folder.
2. Check the `DATA_FOLDER` variable at the top of the script — adjust to match your
   package's data folder name (common names: `data`, `Data`, `01_data`, `raw`).
3. Run from the package root:
   ```bash
   python generate_data_hash_report.py
   ```
4. This produces `data_hash_report.csv` in the package root.
5. Delete the script from the package after running — it should not be in the final ZIP.

**Option B — Use the official World Bank tool:**
https://github.com/worldbank/wb-reproducible-research-repository/tree/main/resources/generate_hash

**What gets hashed:** All files inside the data folder (raw data only, not outputs
or code). If the package has both public and private data, hash all data that
was used for verification, even if restricted data won't be in the public package.

---

## Step 4 — Verify the README covers these fields

Before zipping, do a final README check:

- [ ] Data availability statement present (or separate DAS file)
- [ ] Instructions for how to run (which file, in what order)
- [ ] Which line to change for a new machine's directory
- [ ] Software version specified
- [ ] Mapping of outputs to code (or note in README about linkage table)
- [ ] Rights statement present
- [ ] README is now `README.pdf`

---

## Step 5 — Assemble the ZIP

The final ZIP must have this exact structure:

```
[PACKAGE_ID].zip
├── README.pdf
├── LICENSE.txt
├── reproducibility_report_[PACKAGE_ID].pdf
├── data_hash_report.csv
├── comparison_report.csv          ← ONLY if package has accessible or limited-access data
└── Reproducibility package/
    ├── [all code files]
    ├── [data files — include if data is open/public]
    ├── ado/                       ← Stata only: all installed packages
    │   └── [package files]
    ├── renv.lock                  ← R only
    ├── .Rprofile                  ← R only
    ├── renv/activate.R            ← R only
    └── environment.yml            ← Python/conda only
        OR requirements.txt        ← Python/pip only
```

**Key rules:**
- `README.pdf`, `LICENSE.txt`, `reproducibility_report_*.pdf`, `data_hash_report.csv`,
  and `comparison_report.csv` go at the **TOP LEVEL** of the ZIP — not inside the
  `Reproducibility package/` subfolder. This ensures immediate visibility.
- The `Reproducibility package/` subfolder contains the actual code, data, and
  dependency environment files.
- Data files: include only if data is open/public. Do not include restricted or
  embargoed data.
- `comparison_report.csv` is only required if the package contains accessible data
  (public but no redistribution) or limited-access data. Created using the
  [Dataset Comparison Tool](https://github.com/worldbank/wb-reproducible-research-repository/tree/main/resources/compare_datasets).

**To create the ZIP:**
- On Windows: select all items → right-click → "Compress to ZIP file"
- On Mac: select all items → right-click → "Compress items"
- On Linux/terminal: `zip -r [PACKAGE_ID].zip README.pdf LICENSE.txt reproducibility_report_[PACKAGE_ID].pdf data_hash_report.csv "Reproducibility package/"`
- Name the ZIP exactly: `[PACKAGE_ID].zip` (e.g. `RR_KEN_2026_585.zip`)

---

## Step 6 — Metadata Checklist

Before publishing, verify these fields in the Metadata Editor:

### Auto-filled fields (verify and correct):
- [ ] **Primary ID**: matches package folder name exactly (e.g. `RR_KEN_2026_585`)
- [ ] **Title**: "Reproducibility package for [Paper Title]"
- [ ] **Authors**: all have name, affiliation, and email
- [ ] **Abstract**: no formatting issues; matches paper abstract
- [ ] **Geographic area**: correct ISO-3 code(s) — use `WLD` for multi-country, or
  region codes `LAC`, `MNA`, `SSA`, `AFR` for regional papers
- [ ] **Software**: version number added (e.g. "Stata 18.0 MP")
- [ ] **Scripts**: ZIP file name matches package ID; notes include
  "Computational reproducibility verified by the Development Impact Analytics Team, World Bank."
- [ ] **License**: Modified BSD3 with URL https://opensource.org/license/bsd-3-clause/

### Manual fields — Data Section:
For each dataset, fill in:
- **Dataset name**
- **Access policy** — choose the most restrictive that applies:
  - Open data (included in package)
  - Open data (not included — file size)
  - Accessible (public but no redistribution)
  - Limited-access (requires purchase/approval)
  - Forthcoming in Microdata Library
  - Restricted — no documented access
  - Restricted — custom license, authors only
- **Date accessed** (YYYY-MM)
- **URL** (if publicly available)
- **Notes**: source citation, file location in package, key indicators

**Overall Data Availability Statement** — choose the most restrictive:
- `All data sources are publicly available and included in the reproducibility package.`
- `All data sources are publicly available but not all are included in the reproducibility package.`
- `Some data is restricted and has not been included in the reproducibility package.`
- `All data is restricted and has not been included in the reproducibility package.`
- `Some/All data is forthcoming in the World Bank Microdata Library.`

### Manual fields — Reproducibility Section:
- **Reproduction Instructions**: paste the "How to run" section from the README
  (or Main Findings section from the report), adapted for an external user
- **Technology Requirements**: `~[X] minutes run time`
- **Technology Environment**:
  ```
  OS: [OS]
  Processor: [Processor]
  Memory: [Memory GB]
  Software: [Software + version]
  ```

### External Resources to upload:
- `README.pdf` — Resource type: Document, Other
- `reproducibility_report_[PACKAGE_ID].pdf` — Resource type: Document, Other
- `[PACKAGE_ID].zip` — Resource type: Program/script

### Tags to verify:
- **DOI**: add after publication
- **Data Access**: Open data / Accessible data / Limited-access data / Restricted data
- **Code Access**: Open code / Restricted code / No code

---

## Step 7 — Publish

1. Draft catalog entry on QA
2. Send QA link to reproducibility initiative TTL for review
3. Once approved, publish to PROD
4. Note: publishing to PROD deletes the DOI — add it back manually via the admin portal

---

## Step 8 — Send Final Email to Authors

```
Dear [Author Name],

I hope this message finds you well. Thank you for your submission and
your commitment to reproducibility.

We are pleased to inform you that your paper, "[Paper Title]," has been
successfully verified as reproducible using the provided package. I have
attached our reproducibility verification report.

Your package is now listed in our Reproducible Research Repository:
[INSERT LINK]

The DOI for your package will be added to the entry within the next few days.

This concludes the review. You may now proceed to submit the PRWP form
(https://survey.wb.surveycto.com/collect/world_bank_policy_research_working_papers?caseid=undefined)
to begin the publication process. One of the fields will ask for the link
to your package — use the link above.

We would also appreciate your feedback on the process:
https://survey.wb.surveycto.com/collect/reproducibility_verification_feedback_form_2025?caseid=

Best regards,
[Your Name]
PRWP Reproducibility Verification Team
reproducibility@worldbank.org
```

---

## Step 9 — Update GitHub Dashboard

After publishing:
- [ ] Update issue status to `Published with missings` or `Done`
  - `Published with missings`: thumbnail pending, paper DOI/URL/PRWP number not yet available
    → add label `Pending in RRR: thumbnail` and/or `Pending in RRR: data`
  - `Done`: package is fully finalized
- [ ] Add total time spent on the review (include all team members' time)
- [ ] Add total number of submissions this review took
- [ ] Close the GitHub issue with a summary comment

---

## Done!

The package is published. The review is complete. ✅

**Post-publication reminders** (do these when the paper is published):
- Replace thumbnail with screenshot of the published paper
- Add publication number to Description field (e.g. "Policy Research Working Paper No. 11165")
- Add published paper URL and DOI
- If data was forthcoming: verify it matches the version used in review, then update URL/notes
