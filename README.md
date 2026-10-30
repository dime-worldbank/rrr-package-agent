# Reproducibility Package Reviewer Agent

> [!WARNING]
> **Work in progress.** This agent and its skills are still under active development. Skills, file layouts and outputs may change without notice, and every result must be checked by a human reviewer before it is used or sent to authors.

An AI agent that helps the World Bank Reproducibility Verification Team review reproducibility packages for the [Reproducible Research Repository](https://reproducibility.worldbank.org/). It walks a reviewer through the full workflow, from the first completeness check to the final pre-publication review, and drafts the reports, logs and author emails along the way.

The skills follow the open [Agent Skills](https://agentskills.io) standard, so they can be used with any agent that supports it.

## Workflow

The agent works through five skills, always in order. Each skill must finish before the next one starts.

| Step | Skill | What it does | Main outputs |
|------|-------|--------------|--------------|
| 1 | [Completeness check](.agents/skills/completeness-check/SKILL.md) | Checks the manuscript, README, data availability statement and raw vs. processed data; flags Bank-produced data that needs Microdata Library archiving | Completeness checklist, draft author email if items are missing |
| 2 | [Run package](.agents/skills/run-package/SKILL.md) | Sets up a clean environment (Stata ado folder, `renv`, `requirements.txt`/`environment.yml`), runs the package twice under local Git, and checks output stability | Run log |
| 3 | [Create report](.agents/skills/create-report/SKILL.md) | Collects exhibit results, runtime and system details and fills in the LaTeX report template | `verification_report_[PACKAGE_ID].tex` |
| 4 | [Prepare publication](.agents/skills/prepare-publication/SKILL.md) | Adds the BSD-3 license, converts the README to PDF, hashes the data, assembles the ZIP and prepares metadata | `LICENSE.txt`, `README.pdf`, `data_hash_report.csv`, `[PACKAGE_ID].zip`, `[PACKAGE_ID].json` |
| 5 | [Pre-publication review](.agents/skills/prepublication-review/SKILL.md) | Scans the final ZIP for personally identifiable information and checks the Metadata Editor JSON against the protocol, the ZIP and the report | `prepublication_review_[PACKAGE_ID].md`, a row in `report/prepublication_log.md` |

You can start a step by name ("step 1", "run the code", "create the report", "PII check", …). See each `SKILL.md` for the full list of trigger phrases.

## Repository structure

```
rrr-package-agent/
├── .agents/skills/               ← the five workflow skills (instructions, scripts, templates)
├── .github/
│   └── copilot-instructions.md   ← project instructions for GitHub Copilot
├── CLAUDE.md                     ← project instructions for Claude Code
├── package/                      ← put the package to review here (not tracked by Git)
│   └── RR_WLD_2026_XXX/
└── report/                       ← everything the agent produces (not tracked by Git)
    └── RR_WLD_2026_XXX/
```

`package/` and `report/` are ignored by Git so that submitted data and review outputs are never committed.

## Getting started (VS Code)

The default setup is VS Code with an AI agent extension. The skills are plain Markdown and scripts, so other agent environments that support Agent Skills should also work; instructions for those are still to be written.

### Prerequisites

- Git
- VS Code
- An AI agent extension (e.g. GitHub Copilot or Claude Code) and a license for it
- The software the package under review uses (Stata, R and/or Python)
- Some steps use extra tools:
  - Python 3 (hash report, PII and metadata scripts)
  - R with `haven`, `readxl` and `data.table` (data PII scan, variable inventory)
  - A LaTeX distribution or Overleaf (to compile the report)
  - `pdftotext` (metadata checks)

### 1. Clone the repository

Use any Git client (GitHub Desktop, GitKraken, …) or the command line:

```bash
git clone https://github.com/dime-worldbank/rrr-package-agent.git
```

Then open the `rrr-package-agent` folder in VS Code.

### 2. Add a package to review

Copy the package into its own folder under `package/`, named with the package ID, for example `package/RR_KEN_2026_585/`. This is the only folder you need to change.

Package IDs use the format `TYPE_ISO3_YEAR_NUMBER`:

- `RR`: Policy Research Working Paper
- `PP`: Published Paper
- `FR`: Flagship / Report

### 3. Start the review

Open the agent chat and tell it you have a new submission. It will ask for:

1. The package ID
2. The paper title
3. The software used (Stata / R / Python)
4. Your name

It then starts step 1 and reads the files in `package/[PACKAGE_ID]/` directly. All outputs are saved to `report/[PACKAGE_ID]/`.

## Ground rules

- **Never skip steps.** Each skill builds on the outputs of the one before it.
- **The reviewer stays in charge.** The agent drafts author emails but never sends them; review every draft before sending.
- **Local Git only.** The Git repository created in step 2 to track changes must never be pushed to GitHub.com.
- **Document as you go** in the package's GitHub issue.
- **Escalate to the coordinator** when outputs are unstable and can't be resolved, Bank-produced data is not yet in the Microdata Library, restricted data has no access instructions, or a second resubmission still doesn't reproduce.

## Contributing

This project is still taking shape. If you find a problem with a skill or have a suggestion, please open an issue or a pull request.
