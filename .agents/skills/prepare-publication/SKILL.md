---
name: prepare-publication
description: >
  Run this skill for step 4 of a PRWP reproducibility review — after the report is
  complete and exhibits have been verified. Triggers when a reviewer says "prepare
  the package", "publication prep", "step 4", "zip the package", "add the license",
  "create the hash report", "prepare for publication", "publish the package", or
  "finalize the package". Guides adding the MIT license, converting README to PDF,
  generating the data hash report, assembling the final ZIP structure, and preparing
  metadata. Bundled assets: LICENSE_template.txt, generate_data_hash_report.py.
---

# Skill 4 — Prepare Publication

## What this skill does
Assembles the final reproducibility package for publication on
[reproducibility.worldbank.org](https://reproducibility.worldbank.org/).

Produces:
1. `LICENSE.txt` (MIT License, year updated)
2. `README.pdf` (converted from README if not already PDF)
3. `data_hash_report.csv` (SHA-256 hashes of all data files)
4. `[PACKAGE_ID].zip` with correct internal structure
5. `[PACKAGE_ID]_merge.json` — dataset, software and run metadata to paste into the Reproducibility File Generator app (Step 6b)

**Do not start this skill if the report says the package does not reproduce.** Send the
report to the authors (Skill 3) and wait for the resubmission.

**Every change to the package is committed.** The package folder `package/[PACKAGE_ID]/` is
tracked by the local Git repo from Skill 2 (helper: `S=.agents/skills/run-package/scripts/track_package.py`;
if `report/[PACKAGE_ID]/evidence/package.git` does not exist, run `python $S init --id [PACKAGE_ID] --label step4-start` first).
After each step below that adds, edits, moves or removes a file, run
`python $S commit --id [PACKAGE_ID] --label step4-[what] --note "[what and why]"`, with labels
`step4-structure`, `step4-license`, `step4-readme`, `step4-hash-report`, `step4-deletions`.

Assets bundled in this skill:
- `assets/LICENSE_template.txt` — the MIT license text
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
followed by the full MIT License text. Reference URL for the license:
https://opensource.org/license/mit

---

## Step 2 — Convert README to PDF

The README **must** be in PDF format in the final package.

- If the README is already a PDF: rename to `README.pdf` if not already named that.
- If the README is Markdown (`.md`): convert to PDF using:
  - **Pandoc** (recommended): `pandoc README.md -o README.pdf`
  - **VS Code**: use the Markdown PDF extension
  - **Online**: paste into a Markdown-to-PDF converter
- If the README is a Word doc (`.docx`): save/export as PDF, name it `README.pdf`
- Check the converted PDF with `pdfinfo` and `pdftotext -layout README.pdf -`, not by
  opening its pages as images. Open a page as an image only if the text shows a problem
  (missing sections, broken tables), and only that page.
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

**Private data (data not in the workspace):** do not hash anything. Copy
`package/[PACKAGE_ID]/data_hash_report_prerun.csv` to `data_hash_report.csv`; it was made on the
secure machine from the data as received. `variable_inventory.csv` is already in the bundle, so
skip Step 3b, and Step 3c has nothing to delete. Keep empty placeholder folders where the private
data lived, and keep the outputs in the package.

**Do not delete any restricted, limited-access, or forthcoming data files yet.**
Step 3b (variable inventory) still needs to read those files. Deletion happens in
Step 3c, after both the hash report and the variable inventory are done.

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

## Step 3c — Delete Restricted, Limited-Access, or Forthcoming Data Files

Only run this step after **both** Step 3 (hash report) and Step 3b (variable inventory,
if applicable) are complete — this is the last chance to read those files before they're
gone from the package.

**Headless, or whenever the reviewer cannot confirm: delete nothing.** Leave those files out
of the ZIP with `--exclude` in Step 6 and list them in your summary; data files are not in Git,
so a deletion cannot be undone.

1. Using the completeness check's data classification, list every file/folder that is
   Restricted, Limited-access, or Forthcoming (Microdata Library) — i.e. everything that
   is not Open.
2. Show the reviewer the exact list of files/folders to be deleted and what will be kept,
   and get explicit confirmation before deleting anything (this is a bulk, hard-to-reverse
   action).
3. Delete the confirmed files, then let the reviewer know what was deleted and ask them to
   confirm everything was removed before proceeding to Step 4.

---

## Step 4 — Clean up system and version-control files

Before zipping, remove all files that should never be in the final package:

**Delete all `.DS_Store` files (macOS system files):**
```bash
find "[PACKAGE_DIR]" -name ".DS_Store" -delete
```

**Do not delete `.git`, `.gitignore` or `.gitattributes`.** The ZIP helper in Step 6 never puts
them (or `.DS_Store`, `Thumbs.db`, `~$` lock files, `__pycache__`) in the ZIP, and the `.git`
file in the package is only a pointer: the history lives in `report/[PACKAGE_ID]/evidence/package.git`
and must survive so the reviewer can check every change. Commit the clean-up as `step4-deletions`.

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
1. Arrange `package/[PACKAGE_ID]/` like the structure above: move the code and data folders
   into `Reproducibility package/`, put the top-level files next to it, copy
   `reproducibility_report_[PACKAGE_ID].pdf` in from `report/[PACKAGE_ID]/`, and commit
   (`step4-structure`). The manuscript and anything else left at the top level is not shipped.
2. Build and check it:
   ```bash
   python $S zip --id [PACKAGE_ID] --exclude "Reproducibility package/[non-public data folder or file]"
   python $S changes --id [PACKAGE_ID]
   ```
   `zip` writes `report/[PACKAGE_ID]/[PACKAGE_ID].zip` straight from the package folder (no copy
   of the package is made), refuses to run while changes are uncommitted, and checks every file
   in the ZIP against the last commit (`evidence/zip_manifest.csv`, `evidence/zip_check.json` with
   the ZIP's SHA-256). `--exclude` is repeatable and leaves an empty placeholder folder.
   `changes` updates `evidence/AI_CHANGES.md` with everything this skill changed.
3. Do not zip by hand: a ZIP made another way is not checked against the history.


---

## Step 6b — Prepare Metadata JSON (datasets, software, instructions)

Draft the dataset and run sections of the Metadata Editor entry and save them as
`report/[PACKAGE_ID]/[PACKAGE_ID]_merge.json`. The reviewer pastes (or uploads) this file in
the **Reproducibility File Generator** app under "Add Datasets & Reproduction Info", clicks
**Merge & Preview**, then publishes from the app. The app builds everything else from the
SurveyCTO submission (title, authors, abstract, topics, data statement, scripts, license,
contacts, DataCite).

**Format: a flat JSON object with exactly these five top-level keys.** Do not wrap them in
`project_desc` and do not add other keys; the app ignores anything else.

```json
{
  "datasets": [ { "name": "...", "note": "...", "access_type": "...", "license": "...", "citation": "...", "uri": "..." } ],
  "software": [ { "name": "Stata", "version": "19.5 MP" } ],
  "technology_requirements": "Runtime ~ 2 hours.",
  "technology_environment": "Paper exhibits were reproduced on a computer with the following specifications:\n• OS: ...\n• Processor: ...\n• Memory available: ...",
  "reproduction_instructions": "To reproduce the findings in this paper, a replicator must:\n1. ...\n2. ..."
}
```

Validate it before handing it over: `python -m json.tool report/[PACKAGE_ID]/[PACKAGE_ID]_merge.json`.
`report/RR_BRA_2026_751/metadata_RR_BRA_2026_751.json` is a finished example of this format.
For the `datasets` entries, use the finished Metadata Editor exports in `assets/` as models:
`RR_IDN_2026_708.json` (restricted and author-constructed data), `RR_PNG_2026_696.json`,
`RR_COL_2026_743.json` (their datasets sit under `project_desc`; copy the entry style, not the nesting).

Sources: the README's Data Availability Statement, the completeness check, the final
reproducibility report, `data_hash_report.csv` and `variable_inventory.csv`.

**Fields to draft** (exactly these five keys, nothing else — no `data_statement`, `title_statement`,
`scripts` or `methods`; the app builds those from the survey):
- `software` — name and the version used in verification (from the reproducibility report),
  e.g. `[{"name": "Stata", "version": "19.5 MP"}, {"name": "R", "version": "4.4.0"}]`.
  This replaces the software list the app takes from the survey.
- `technology_requirements` — runtime (e.g. `"Runtime ~ 2 hours."`) plus any disk/memory notes
- `technology_environment` — `"Paper exhibits were reproduced on a computer with the following
  specifications:"` followed by OS, processor and memory available, one per line. Do **not** list
  software versions here; they go only in `software`.
- `reproduction_instructions` — starts "To reproduce the findings in this paper, a replicator must:", then numbered steps: secure
  data access, which script to open, which line to change, run order. Keep it short:
  - **Step 1 (data access) only points to the Datasets section**, e.g. "Secure data access: obtain
    the restricted and limited-access datasets as described in the Datasets section and place them
    in the locations listed there." Do **not** put contacts, emails, data use agreements, catalog
    numbers, registration steps or vendor details here; those go in the dataset's `note`.
  - **Format every file, folder, variable and script name in backticks**, consistently (never mix
    backticked and plain names): `` `RawData/RESTRICTED_DATA/` ``, `` `micro_world.dta` ``,
    `` `Master.m` ``, `` `run_PSVAR.m` ``.
  - **Stata do-files are the exception**: the `.do` extension gets rendered as a link, so write the
    name without the extension followed by "do-file": "open the `` `main` `` do-file", "run the
    `` `code/A_collect_firm_data` `` do-file". Never write `main.do`.
- `datasets` — one entry per dataset (see rules below)

**Dataset entry rules:**
- **Source data only, not intermediate data.** List the datasets the authors obtained (raw
  downloads, licensed extracts, surveys, author-built crosswalks). Do not create an entry for a
  file the code builds from other datasets (analysis panels, merged files, saved estimation
  results); mention it as "(derived)" in the `note` of the dataset it comes from, or in
  `reproduction_instructions` if users must rebuild it.
- **Name = the dataset title used in the citation**, without the producer prefixed: "Global Debt
  Database" (citation: "International Monetary Fund. (2025). Global Debt Database ..."), not
  "International Monetary Fund (IMF) Global Debt Database". The producer belongs in the citation.
- **No acronyms in names where avoidable.** Spell names out in English, giving the acronym in
  parentheses only if it is how the source is known: "World Integrated Trade Solution (WITS)
  Product Concordance", "Annual Manufacturing Survey, plant-level microdata" (not "BPS
  Statistik Industri"), "Input-Output (IO) Sectors to Standard Classification of Indonesian
  Business Fields (KBLI) Concordance". Prefer English names over local-language titles.
- **One entry per dataset, not per file.** If several files come from the same source or
  compilation, list all filenames in a single entry's `note`
  (`"Filename: Data/Raw/a.dta; Data/Raw/b.dta."`).
- **`note`** — start with `Filename: <path>.`, then the source, what the data contains, and
  what it is used for in the code. For data not in the package, add "A list of variables is
  provided in variable_inventory.csv, and the file hash is in data_hash_report.csv."
- **Access details live in the `note` of each dataset not in the package**, not in
  `reproduction_instructions`: who to contact (name, institution, email) or where to buy/register,
  any data use agreement or approval, catalog/registration steps, and where to place the file in
  the package folder (e.g. "Place the file in RawData/RESTRICTED_DATA/.").
- **Author contact sentence at most once per JSON.** "For more details on the data, interested
  users can reach out to one of the authors at <author email>." goes only in the entry where the
  authors are the access route (e.g. restricted data they hold). Do not repeat it in every note,
  and do not add it to licensed/commercial data obtained from a vendor.
- **Restricted/confidential data** (not in the package):
  - `access_type`: `"Data is restricted, and it is not included in the reproducibility package."`
  - `license`: `"Confidential"`
  - `citation`: end with `"Unpublished data."` (plus how it was accessed, e.g. "Accessed
    through a World Bank collaboration.")
  - `note`: end with how to request access (the data owner's contact and conditions), per the
    access-details rule above.
- **Author-constructed data** (concordances, crosswalks, compilations included in the package):
  - `access_type`: `"Data is included in the reproducibility package."`
  - `license`: `"Custom License"`
  - `citation`: `"Authors' compilation, World Bank. (YEAR). <Dataset name>"`
- **Public data included in the package:**
  - `access_type`: `"Data is publicly available and included in the reproducibility package."`
  - `license`: the provider's terms (e.g. `"Public"`, `"Central Statistics Agency (BPS) Terms of
    Use"`), with `license_uri` when the provider has a terms-of-use page
  - `uri`: the download page
- **Data no longer publicly available in the version used** (e.g. an older vintage): say so in
  `access_type` and the `note`, link the current public version in `uri`, add the author contact.
- **Citation format:** `Producer. (YEAR). Title [dataset]. Publisher. URL` — always include the
  year and the URL when there is one.

Flag any README `[PLEASE FILL]` or missing source information to the reviewer rather than
guessing.


---
## Step 7 — Send Final Email to Authors

**Do this only after Skill 5 (pre-publication review) returns "Ready to go live"** and the package
is live on the Reproducible Research Repository. Never send PII-flagged packages live.

Write an email to the authors with the following template, customizing as needed, and save the draft as
`report/[PACKAGE_ID]/emails/4_final_published.md`. Attach the reproducibility verification report and include the link to the package in the Reproducible Research Repository. 

```
Dear [Author Name],

I hope this message finds you well. Thank you for your submission and
your commitment to reproducibility.

We are pleased to inform you that your paper, "[Paper Title]," has been
verified as reproducible using the package you provided. Our
reproducibility verification report, with detailed findings, is attached.

Your package is now listed in our Reproducible Research Repository:
[INSERT LINK]. The DOI will be added to the entry within the next few days.

This concludes the review of your package. You can now submit the PRWP form
(https://survey.wb.surveycto.com/collect/world_bank_policy_research_working_papers?caseid=undefined)
to start the publication process. When the form asks for the link to your
package, use the link above.

We would also appreciate your feedback on the process. If you have a
moment, please share your thoughts through this anonymous feedback form:
https://survey.wb.surveycto.com/collect/reproducibility_verification_feedback_form_2025?caseid=

Please don't hesitate to reach out if you have any questions.

Best regards,
[Your Name]
PRWP Reproducibility Verification Team
reproducibility@worldbank.org
```

---

