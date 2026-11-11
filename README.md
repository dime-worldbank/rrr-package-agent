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
| 2 | [Run package](.agents/skills/run-package/SKILL.md) | Sets up a clean environment (Stata ado folder, `renv`, `requirements.txt`/`environment.yml`), runs the package twice under local Git, and checks output stability | `run_log.md`, run evidence in `evidence/` |
| 3 | [Create report](.agents/skills/create-report/SKILL.md) | Compares every exhibit with the outputs and writes the report. If the package does not reproduce, the review stops here and the report goes to the authors | `verification_report_[PACKAGE_ID].md` and `.tex`, `reproducibility_report_[PACKAGE_ID].pdf` |
| 4 | [Prepare publication](.agents/skills/prepare-publication/SKILL.md) | Adds the MIT license, converts the README to PDF, hashes the data, assembles the ZIP and prepares metadata | `LICENSE.txt`, `WB-IGO-RIDER.txt`, `README.pdf`, `data_hash_report.csv`, `[PACKAGE_ID].zip`, `[PACKAGE_ID]_merge.json` (paste into the Reproducibility File Generator app) |
| 5 | [Pre-publication review](.agents/skills/prepublication-review/SKILL.md) | Scans the final ZIP for personally identifiable information and checks the Metadata Editor JSON against the protocol, the ZIP and the report | `prepublication_review_[PACKAGE_ID].md`, a row in `report/prepublication_log.md` |

After the last step, a final stage writes `ai_use_summary.md` for the GitHub issue (see [AI use summary](#ai-use-summary)).

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
├── report/                       ← everything the agent produces (not tracked by Git)
│   └── RR_WLD_2026_XXX/
│       ├── emails/               ← draft emails, numbered in sending order; you send them
│       ├── evidence/             ← what the AI changed and proof the code ran
│       └── ai_use_summary.md     ← paste into the GitHub issue
├── scripts/                      ← headless_review.py, chat_usage.py, ai_summary.py
└── docs/review_desk.html         ← open in a browser: command builder and what to check per step
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

There are two ways to run the steps. They write the same files to `report/[PACKAGE_ID]/`, so you can mix them in one review. [`docs/review_desk.html`](docs/review_desk.html) builds the commands for you and lists what to check after each step.

**In the chat, step by step.** Open the agent chat and say which package and which step, for example "start the review of 806" or "step 3 for 806". The agent finds the title, software and your name from the package and from earlier runs, and asks only for what is missing.

**Headless, without supervision (Claude Code).** One command runs all five steps, each in a fresh session, and stops when something needs you:

```bash
python scripts/headless_review.py 806 --title "Paper title"
```

The ID can be the full package ID or just its number. Only the first run needs `--title`; the title, software (detected from the code files), your name (`--reviewer`, else `git config user.name`) and `--private` are remembered for the package. After that:

```bash
python scripts/headless_review.py 806 --status
```

shows the state of each step and what you have to check or send, without running anything, and

```bash
python scripts/headless_review.py 806 --steps next
```

resumes from the first unfinished step. `--steps 3` runs one step and `--steps 3-5` a range. You can also ask for any of these in the chat ("run 806 headless", "where is 806?"): the agent starts the same command.

### Measuring token usage (Claude Code)

Both ways of running a review can report tokens, cost and time per step, in the same table format:

- **Headless** (`scripts/headless_review.py`, all five steps without a chat): writes `report/[PACKAGE_ID]/headless/token_usage.md` and `.csv` as it runs.
- **Chat** (the review done step by step in the agent chat): run this after the review.

  ```bash
  python scripts/chat_usage.py --id RR_WLD_2026_XXX
  ```

  It reads the chat transcripts Claude Code saves in `~/.claude/projects/` and writes `report/[PACKAGE_ID]/chat/token_usage.md` and `.csv`, with one table per chat that mentions the package ID. Each message you send is counted toward the skill the agent opens in reply; follow-up messages count toward the step before. Add `--session <chat id>` to count only the chats that belong to the review. Cost is an estimate at API list price, so chat and headless runs can be compared.

### Checking what the AI changed

Everything a reviewer needs to check the AI's work on a package is in `report/[PACKAGE_ID]/evidence/`, written by [`track_package.py`](.agents/skills/run-package/scripts/track_package.py):

- **`AI_CHANGES.md`**: every file the AI added, edited or removed in the package, with the commit and `file:line`, and a warning on any change to a script that writes exhibits or to an output. Start here.
- **`package.git/`**: the local Git history of `package/[PACKAGE_ID]/` (`initial-package`, one commit per code fix, `first-run`, `second-run`, then one `step4-…` commit per publication action). The package folder only holds a `.git` pointer file, so these work as usual:

  ```bash
  git -C package/RR_WLD_2026_XXX log --oneline
  ```

  ```bash
  git -C package/RR_WLD_2026_XXX diff initial-package..HEAD
  ```

- **`run_times.csv`, `runN_stdout.log`, `runN_hashes.csv`, `run_comparison.csv`**: when each run started and ended, what the main script printed, and the SHA-256 and modification time of every file after each run, including the binary outputs Git ignores (`.dta`, `.xlsx`, `.pdf`).
- **`zip_manifest.csv`, `zip_check.json`**: every file in the final ZIP, checked against the last commit, and the ZIP's own SHA-256.
- **`assumptions.md`**: what the AI assumed, and what it did not do or could not check, one section per step. Working files (install logs, scan results) are here too, so the top level of `report/[PACKAGE_ID]/` holds only what you read, send or publish.

The history is never pushed and never goes into the ZIP. On the private path the reviewer runs the code, so the run evidence is `code_changes.diff` and `hash_comparison.csv` from `private_bundle.py postrun`; `AI_CHANGES.md` points to them and tracking starts with the bundle.

### AI use summary

The last stage of every review writes `report/[PACKAGE_ID]/ai_use_summary.md`, one block of Markdown to **paste into the package's GitHub issue**. `headless_review.py` writes it at the end of every run; after a chat review, run:

```bash
python scripts/ai_summary.py --id RR_WLD_2026_XXX --mode chat --title "Paper title" --reviewer "Your name"
```

It is short: a header line, the package status and AI cost (an estimate at API list price; the per-step detail stays in `token_usage.md`), a reviewer checklist ("I reviewed the AI's changes", then one line per stage with what the AI found), comments (open items found in the files, plus your own) and the time with and without AI. The checklist boxes and the time fields are left empty: the reviewer ticks and fills them in after checking. The script calls no AI and never states that something was verified.

### Headless runs: what stops them

`headless_review.py` checks before each step that the outputs of the step before exist. It stops, with exit code 1 and a `report/[PACKAGE_ID]/headless/BLOCKED_stepN.md` saying what to do, when a prerequisite is missing, the completeness verdict is RETURN TO AUTHORS, a step crashes, runs past `--timeout-min` (60 minutes unless you set it; step 2 has no limit while it runs the package's code) or `--max-budget`, or the package repo has a remote. **A package that does not reproduce always stops before step 4.** Fix the cause and resume with `--steps next`; earlier attempts are kept under time-stamped names and stay in `token_usage.csv`.

## Ground rules

- **Never skip steps.** Each skill builds on the outputs of the one before it.
- **The reviewer stays in charge.** The agent drafts author emails but never sends them; review every draft before sending.
- **Local Git only.** The Git repository created in step 2 to track changes must never be pushed to GitHub.com. Its history stays in `report/[PACKAGE_ID]/evidence/` on the reviewer's machine.
- **The reviewer signs off.** Paste `ai_use_summary.md` into the GitHub issue only after ticking its checklist yourself.
- **Document as you go** in the package's GitHub issue.
- **Escalate to the coordinator** when outputs are unstable and can't be resolved, Bank-produced data is not yet in the Microdata Library, restricted data has no access instructions, or a second resubmission still doesn't reproduce.

## Contributing

This project is still taking shape. If you find a problem with a skill or have a suggestion, please open an issue or a pull request.
