# Part A: PII review

Goal: nothing in the published zip can identify a study participant, respondent, firm contact or
private person. Every finding must be specific: **file, variable/line, PII type, number affected, masked
evidence.**

`scripts/scan_data.R` and `scripts/scan_code.py` do the first pass. Everything below marked
**(manual)** needs you to read the material.

## 1. Inventory and hidden content
- Compare `zip_listing.txt` with the unzipped tree.
- Look for: `.git/` (run `git log --all` and `git ls-tree -r <commit>` for every commit; **files deleted from the
  working tree but still in `.git` count as shipped**; extract them with `git show` to a temp folder and
  review them), nested zips/rar/7z (unpack and review), `__MACOSX`, `~$` lock files, `.Rhistory`,
  `.Rproj.user/`, `.ipynb_checkpoints`, `.Rdata` autosaves, `*.log`/`*.smcl` logs (they print data), and
  Jupyter notebooks with stored outputs (`"outputs"` in `.ipynb`).

## 2. README / DAS (manual)
- Note every dataset the README calls confidential, restricted, limited-access, or "contains PII".
- **If any of those files is in the zip, that is a finding** (High if it is respondent microdata).
- Note the population. Are any participants minors (under 18)? Is this a vulnerable group (refugees,
  GBV survivors, patients, beneficiaries)? These raise severity.

## 3. Data files
Types: .dta .sav .por .csv .tsv .txt .xlsx .xls .xlsm (every sheet) .rds .RData/.rda .parquet .json
.sas7bdat .shp/.dbf .gpkg .geojson .kml.

For each file:
- List the variables with labels (the scanner does this).
- For **every string variable**: count unique values, look at masked examples, and regex-scan **all rows** for
  emails, phone numbers (use country mobile formats, e.g. MX 10 digits, PK `03xxxxxxxxx`, NG `0[789]0xxxxxxxx`,
  KE `07xxxxxxxx`), national IDs (MX CURP/RFC/NSS, IN Aadhaar 12 digits, PK CNIC `xxxxx-xxxxxxx-x`, etc.) and URLs.
- **(manual)** Read the free-text fields: "other, specify", comments, notes, remarks, reasons, `_os`, `_oth`,
  call notes, Qualtrics/SurveyCTO metadata. Look for personal names, addresses and phone numbers.
  Pull out the unique values and search for name markers (Mr/Ms/Sr/Sra/"name is"/common local first
  names), then spot-read them.
- **Value labels.** Names, firms, emails and phone numbers often hide there (enumerator/supervisor IDs,
  school or clinic names, village names).
- Flag variables named or labelled: name, phone, mobile, email, address, village, GPS/lat/lon,
  birth/DOB, national ID, device/SIM/IMEI, IP address, Qualtrics `IPAddress`/`LocationLatitude`/
  `RecipientEmail`, SurveyCTO `deviceid`/`simid`/`caseid`.

## 4. Indirect identifiers (manual)
- Exact GPS: check the decimals and whether points are displaced.
- Exact date of birth, or day-level dates of events.
- Small geography (village/ward/school/settlement) combined with age, sex and other traits. Count how many
  records are unique on the combination. Note whether the key that names the geography is shipped.
- Small cells in aggregates (count = 1).
- IDs that embed information, e.g. a DOB inside the ID: test whether the digits parse as dates and correlate with age.
- Original survey/admin IDs that undo the masking (an "anonymized" ID that is just the original, or a
  crosswalk shipped somewhere).

## 5. Code and documents
- Emails, phone numbers, names and **hard-coded respondent details** in code. A common pattern is
  `replace id = "…" if email == "…"` linking tables, manual corrections keyed on original IDs, or `list`/`browse`
  output saved in logs.
- Staff UPIs/user paths (`C:/Users/wb123456`): Low, optional cleanup.
- PDFs/docs/images: participant lists, photos, screenshots of data, consent forms, signed documents.
- Reproducibility report and README: authors' and reviewers' work emails are fine (they are public contacts).

## 6. Context
- An unmodified official public-use release (LSMS, DHS, MICS, ENOE, NSS, …): its standard
  quasi-identifiers are **borderline/Low**, but direct identifiers (names, phones) are still PII. Redistributing
  licensed data is a licence issue (Part B), not PII.

## Severity
| Severity | Examples |
|---|---|
| **High** | Names, phones, emails, addresses or exact GPS of respondents/participants (in data **or code**); any identifying data on **minors** (write "High (minors)"); raw identified survey or admin data, including in `.git`; README-restricted microdata shipped |
| **Medium** | Names in some free-text rows; staff/enumerator names plus detailed location; quasi-identifiers that make most records unique *and* the key to the geography is shipped; confidential admin data with small cells |
| **Low** | Borderline items, mostly standard quasi-identifiers in official public releases; staff UPIs/paths; a single unexplained small cell |

PII status line for the report: `PII found (High|Medium|Low)` or `No PII found` or `No PII found (borderline)`.

## Proposed fix (always give one)
Be concrete. Example: "Delete lines 1036–1077 of `programs/e2_….do` and replace them with a comment saying the
email-to-ID crosswalk is kept with the restricted data; re-zip." Or "drop `s1aq09` from `AGSEC1.dta`".
Say whether the fix needs the **authors** (data or code change) or can be done by the **team**.
