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
- `assets/variable_inventory.R` — script to inventory variables in inaccessible datasets

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
- If the README is inside a subfolder of the package (e.g. `reproducibility_package/`), copy it to the top level, rename it to `README.pdf`, and **delete the original from the subfolder**. The README must exist only at the top level of the package folder.

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

After data is hashed we will need to delete files that are restricted, limited access or forthcoming in the Microdata Library, so we want to have the hashes of all data files before we delete any. Delete files, let the user know what was deleted, and ask them to confirm everything was deleted before proceeding.

---

## Step 3b — Generate Variable Inventory for Inaccessible Datasets

Run this step when the package contains datasets that **could not be included** (restricted,
limited-access, or privately shared) AND that are **not clearly catalogued** in an official
public repository with a stable URL. This provides minimum documentation of dataset content
for future replicators.

**When to run:**
- Any dataset marked as Limited-access, Restricted, or Private in the completeness check
- Especially when access instructions are vague (e.g., "contact the Poverty Economist")
  and archiving in an official repository was not completed before publication

**How to run:**

1. Copy `assets/variable_inventory.R` to a temporary working location (not inside the
   package folder — the script should not end up in the final ZIP).

2. Open the script and set `data_dir` (line 11) to the folder containing the private
   data files. If data is spread across multiple folders, run the script once per folder
   or adjust the path to a common parent folder (the script searches recursively).

   ```r
   data_dir <- "/path/to/private/data/folder"
   ```

3. Run the script in R. It will read only the first row of each file (no data is
   extracted beyond column names) and produce `variable_inventory.csv` in `data_dir`.

4. Move `variable_inventory.csv` to the report folder:
   `report/[PACKAGE_ID]/variable_inventory.csv`

5. Include `variable_inventory.csv` in the final ZIP at the **top level** alongside
   `data_hash_report.csv`.

**Supported file types:** `.csv`, `.tsv`, `.dta`, `.sav`, `.rds`, `.rdata`, `.xlsx`, `.xls`

**What the output contains:**
- `dataset` — filename
- `n_variables` — number of variables/columns
- `variable_list` — semicolon-separated list of variable names

**Note:** The variable inventory is a documentation artifact, not a data file. It does
not expose confidential data — only variable names and counts.

---

## Step 4 — Clean up system and version-control files

Before zipping, remove all files that should never be in the final package:

**Delete all `.DS_Store` files (macOS system files):**
```bash
find "[PACKAGE_DIR]" -name ".DS_Store" -delete
```

**Delete the `.git` folder and all git config files:**
```bash
rm -rf "[PACKAGE_DIR]/reproducibility_package/.git"
rm -f "[PACKAGE_DIR]/reproducibility_package/.gitattributes"
rm -f "[PACKAGE_DIR]/reproducibility_package/.gitignore"
```

Verify nothing remains:
```bash
find "[PACKAGE_DIR]" -name ".DS_Store" -o -name ".git" -o -name ".gitattributes" -o -name ".gitignore"
```
The command should return no output.

---

## Step 5 — Verify the README covers these fields


Before zipping, do a final README check:

- [ ] Data availability statement present (or separate DAS file)
- [ ] Instructions for how to run (which file, in what order)
- [ ] Which line to change for a new machine's directory
- [ ] Software version specified
- [ ] Mapping of outputs to code (or note in README about linkage table)
- [ ] Rights statement present
- [ ] README is now `README.pdf`

---

## Step 6 — Assemble the ZIP

The final ZIP must have this exact structure:

```
[PACKAGE_ID].zip
├── README.pdf
├── LICENSE.txt
├── WB-IGO-RIDER.txt
├── reproducibility_report_[PACKAGE_ID].pdf
├── data_hash_report.csv
├── variable_inventory.csv         ← ONLY if package has inaccessible datasets not in official repo
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
## Step 7 — Send Final Email to Authors

Write an email to the authors with the following template, customizing as needed. Attach the reproducibility verification report and include the link to the package in the Reproducible Research Repository. 

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

