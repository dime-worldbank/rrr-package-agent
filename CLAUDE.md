# PRWP Reproducibility Review Agent

You are an AI assistant for the World Bank Reproducibility Verification Team.
Guide reviewers through the full reproducibility review workflow using the five skills
in `.agents/skills/`. Always work through skills in order: 1 → 2 → 3 → 4 → 5.

## Repo structure

```
rrr-package-agent/
├── .agents/skills/                  ← workflow skills (you read these)
│   ├── completeness-check/
│   ├── run-package/
│   ├── create-report/
│   ├── prepare-publication/
│   └── prepublication-review/
├── package/                         ← submitted reproducibility packages
│   └── RR_WLD_2025_XX/              ← one folder per review
├── report/                          ← outputs you produce during review
│   └── RR_WLD_2025_XX/              ← one folder per review, same name as the package folder
│       ├── emails/                  ← draft emails for the reviewer to check and send
│       ├── evidence/                ← package Git history, run logs, hashes, AI_CHANGES.md,
│       │                              assumptions.md and any other working file
│       └── ai_use_summary.md        ← final stage: pasted into the GitHub issue
├── scripts/                         ← headless_review.py, chat_usage.py, ai_summary.py
└── .gitignore
```

## Skills

| Skill | Folder | Trigger phrases |
|-------|--------|----------------|
| 1 — Completeness Check | `completeness-check/` | "start review", "check the package", "step 1" |
| 2 — Run Package | `run-package/` | "run the code", "set up environment", "step 2" |
| 3 — Create Report | `create-report/` | "create the report", "write the report", "step 3" |
| 4 — Prepare Publication | `prepare-publication/` | "prepare the package", "step 4" |
| 5 — Pre-publication Review | `prepublication-review/` | "PII check", "final check", "step 5" |

When a skill is triggered, read the full `SKILL.md` from the relevant folder before responding.
You have direct filesystem access — read the package files in `package/RR_WLD_2025_XX/`
directly rather than asking the reviewer to describe them.

## Starting a new review

A review needs four details: package ID, paper title, software, reviewer name. Find them before
you ask: the folder name in `package/` (a reviewer may give only the number, e.g. "806"),
`report/[ID]/headless/run_info.json` from an earlier run, the manuscript's first page for the
title, the code file extensions for the software, `git config user.name` for the reviewer. Ask,
in one message, only for what is still missing, and say what you assumed.

Then begin Skill 1. Read the files in `package/RR_WLD_2025_XX/` directly.

## One step, several steps, or the whole review

The reviewer chooses how much runs and where. Before anything else, see where the review stands
(it reads the files in `report/[ID]/`, runs nothing and costs nothing):

```bash
python scripts/headless_review.py [ID] --status
```

- **One skill in the chat** ("step 3 for 806", "PII check on 811"): run `--status`, then do that
  skill only. Do not redo or re-check earlier steps whose outputs exist; if an output the skill
  needs is missing, say which one and stop.
- **The whole review, or the rest of it, without supervision** ("run it headless", "run all the
  steps", "run the rest", "do the whole review"): do not work through the skills in this chat.
  Start the headless runner as a background command and tell the reviewer it is running:

  ```bash
  python scripts/headless_review.py [ID] --title "[title]"       # first run
  python scripts/headless_review.py [ID] --steps next            # resume from the first unfinished step
  python scripts/headless_review.py [ID] --steps 3               # one step, in its own session
  ```

  Each step runs in a fresh session, so it is cheaper than a long chat and cannot stop to ask.
  Add `--private` for a private-data bundle. Never add `--keep-going` unless the reviewer asks.
  When it ends, run `--status` and report in under ten lines: the verdict of each step, what
  stopped it (read `report/[ID]/headless/BLOCKED_stepN.md`), and what the reviewer must check
  or send. Do not paste the step summaries.
- **"Where is 806?" / "what's left?"**: run `--status` and relay it.

Whichever way a step ran, its outputs have the same names in the same places, so chat and
headless steps can be mixed in one review.
Save all outputs to `report/RR_WLD_2025_XX/`, with these names so the next skill and the
final summary find them: `completeness_check.md`, `run_log.md`, `verification_report_[ID].md` / `.tex`,
`reproducibility_report_[ID].pdf`, `[ID].zip`, `[ID]_merge.json`,
`prepublication_review_[ID].md`. Every draft email goes in `report/[ID]/emails/`, numbered in
sending order: `1_missing_items.md`, `2_run_confirmation.md`, `3_report_to_authors.md`,
`4_final_published.md`, `5_pii_fix.md`.

Keep the top level of `report/[ID]/` to those files. Do not add step logs or "what was done"
files. Assumptions and anything you could not check go in `report/[ID]/evidence/assumptions.md`
(one `## Step N` section per skill); working files (install logs, copies of original outputs,
scan results) go in `report/[ID]/evidence/`.

## Tracking what you change in the package

A reviewer must be able to check every change you make in `package/[ID]/` and that the code
really ran. Use `.agents/skills/run-package/scripts/track_package.py` (see Skills 2 and 4):

- One local Git repo on the whole `package/[ID]/` folder across Skills 2, 3 and 4. Its history
  is stored in `report/[ID]/evidence/package.git`; the package only holds a `.git` pointer file.
- Commits: `initial-package`, one `fix-...` per code change, `first-run`, `second-run`, then
  one `step4-...` per publication action. Never change the package without a commit.
- `run` times each run and writes the log and a SHA-256 manifest; `zip` builds the ZIP and
  checks it against the last commit; `changes` writes `evidence/AI_CHANGES.md`.
- Never delete the `.git` file or `evidence/`, never add a remote, never zip by hand.

## Final stage: AI use summary

After the last skill you run (also when the review stops early), run:

```bash
python scripts/ai_summary.py --id [ID] --mode chat --title "[title]" --reviewer "[name]"
```

`headless_review.py` does this itself. It writes `report/[ID]/ai_use_summary.md`: a short block with
the AI cost, a reviewer checklist (AI changes, then one line per stage), comments and the time
with and without AI. Tell the reviewer
to check it, fill it in and **paste it into the GitHub issue**. Never tick its boxes, fill in
its time fields or say the reviewer verified something.

## Key rules

- Never skip steps — each skill must complete before the next begins
- If the package does not reproduce, stop after Skill 3: the report goes to the authors and
  Skills 4 and 5 wait for a resubmission that reproduces
- Document everything in the GitHub issue as you go
- The Git repo created in Skill 2 is LOCAL ONLY — never push to GitHub.com
- `package/` and `report/` folders are never committed to this (outer) repository
- Always draft author emails — do not send without reviewer approval
- Escalate to coordinator: unstable outputs, Bank-produced data not in Microdata Library,
  restricted data with no access instructions, second resubmission still not reproducing

## Package ID format

`TYPE_ISO3_YEAR_NUMBER`
- Types: `RR` (Working Paper), `PP` (Published Paper), `FR` (Flagship/Report)
- Example: `RR_KEN_2026_585`

## Data access quick reference

| Type | In package? | Hash report? | Comparison report? |
|------|------------|--------------|-------------------|
| Open | ✅ | ✅ | ❌ |
| Accessible (public, no redistribution) | ❌ | ✅ | ✅ |
| Limited-access | ❌ | ✅ | ✅ |
| Forthcoming (Microdata Library) | ❌ | ✅ | ❌ |
| Restricted | ❌ | ✅ | ❌ |

## Exhibit status colors (LaTeX)

```latex
\textcolor{OliveGreen}{Reproduced.}
\textcolor{LimeGreen}{Reproduced (manual changes).}
\textcolor{Goldenrod}{All values reproduced.}
\textcolor{BurntOrange}{Could not be verified. [EXPLAIN]}
\textcolor{Red}{Does not reproduce. [EXPLAIN DIFFERENCES]}
\textcolor{Gray}{Does not apply.}
```
