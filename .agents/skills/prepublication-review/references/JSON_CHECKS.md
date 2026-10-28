# Part B: JSON consistency

This is the final check before a package goes live. The package itself has already been verified and prepared.
Here we only check that the **Metadata Editor JSON** is correct and consistent: with the protocol, with itself, with what
is in the zip, and with the reproducibility report.

`scripts/check_metadata.py` runs everything marked `auto`. Re-check every FAIL/WARN by hand before you report it.
Source: [metadata_protocol.md](https://github.com/worldbank/wb-reproducible-research-repository/blob/main/metadata_protocol.md) (MP), plus the team conventions noted below.

Levels: **Fix** = wrong or contradicts something; must be corrected before going live. **Minor** = wording/format.

## J1. Fields vs protocol (auto)
| # | Check | Level |
|---|---|---|
| J1.1 | Producers = Reproducibility WBG / DECDI / World Bank - Development Impact Department / Verification and preparation of metadata | Minor |
| J1.2 | prod_date / production_date are YYYY-MM-DD; version "1" unless revised | Minor |
| J1.3 | idno is `TYPE_ISO3_YEAR_NUMBER` and matches the package folder | Fix |
| J1.4 | Title = "Reproducibility package for " + `output[0].title` | Fix |
| J1.5 | Each author has name, affiliation, email. **Authors only need to be in `authoring_entity`; author order does not matter, and a missing or differently ordered `output[0].authors` is not flagged** | Fix |
| J1.6 | Geographic codes are ISO-3/region codes; the idno region is among them | Minor |
| J1.7 | Abstract present, no formatting junk | Minor |
| J1.8 | Keywords and topics present. **JEL ids carry a leading space by design. Do not flag it.** | Minor |
| J1.9 | Output type allowed; description = "Policy Research Working Paper (PRWP) ####" (WP) or the journal name (article) | Fix |
| J1.10 | Disclaimer present, not "Default" | Fix |
| J1.11 | Licenses MIT + World Bank IGO Rider, with the protocol URLs | Fix |
| J1.12 | Contacts include reproducibility@worldbank.org | Minor |
| J1.13 | Every software entry has a version | Fix |
| J1.14 | scripts: zip_package = `<ID>.zip`, title = project title, dependencies mention ado/renv/requirements, standard note | Minor |
| J1.15 | Repository = Reproducible Research Repository (World Bank) | Minor |
| J1.19–21 | reproduction_instructions starts "To reproduce the findings…"; technology_requirements has the run time; technology_environment starts "Paper exhibits were reproduced…" and lists OS/processor/memory (software versions belong in `software`, not here) | Minor |
| J1.22–23 | DataCite: creators (Personal + given/family, ROR for WB/WBG/IFC/IMF), titles [title, ID], publisher, types, URL `…/catalog/study/<ID>`, language, year; creators = authors | Fix |
| J1.24 | Tags: DOI, one data access tag, one code access tag | Fix |
| J1.25 | No placeholders (`[…citation…]`, TBD, XX) anywhere in the JSON | Fix |

## J2. Datasets and data statement (auto + manual)
| # | Check | Level |
|---|---|---|
| J2.1 | Each dataset: standard `access_type` sentence ("…and **it** is not included" is accepted); note gives file location(s) and access date | Fix |
| J2.2 | Citation is a real citation ("[dataset]", year), not just a URL; public data has a URL; restricted/limited data has a license | Minor |
| J2.3 | **`data_statement` follows the team template:** *"The reproducibility package relies on N types of data: X, Y and Z. For the source, access type, file location, and citation of each dataset, refer to the Datasets section and the README file."* The old standard sentences ("Some data is restricted and has not been included…") are **not** accepted any more | Fix |
| J2.4 | The types named in data_statement = the set of dataset access types (open, accessible, limited-access, forthcoming, restricted; "not included due to size" counts as open), and N = the number of types | Fix |
| J2.5 | Data access tag = the most restrictive dataset type (restricted > limited-access > forthcoming > accessible > open) | Fix |
| J2.6 | If any data is not included, reproduction_instructions say how to get it | Minor |

## J3. JSON vs package contents (auto + manual)
| # | Check | Level |
|---|---|---|
| J3.1 | Files a dataset lists as restricted / limited-access / accessible / forthcoming are **not** in the zip (if they are, that's also a Part A finding) | Fix |
| J3.2 | Files a dataset lists as "included" are in the zip | Fix |
| J3.3 | Every data file in the zip belongs to a dataset in the JSON (derived/analysis datasets need their own entry or a mention in a note) | Fix |
| J3.4 | Software list matches the code languages in the zip | Fix |
| J3.5 | Scripts named in reproduction_instructions exist; "line N of X" really is the path line | Minor |
| J3.6 | zip_package = the zip's name | Fix |

## J4. JSON vs reproducibility report (auto + manual)
| # | Check | Level |
|---|---|---|
| J4.1 | The report's "relies on N types of data: …" line names the same types as the JSON data_statement and datasets | Fix |
| J4.2 | Software versions match the report | Minor |
| J4.3 | OS / processor / memory match the report | Minor |
| J4.4 | Run time matches the report | Minor |

## How to report
Put only the items that are not PASS in the report's single Changes table (see `assets/review_report.md`), with the
exact new value. Do not list passed checks, false positives from the script, or "not in scope" notes.
