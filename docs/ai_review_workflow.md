# Reviewing AI-assisted reproducibility reviews

Most of the review work is now done by AI: the skills in `.agents/skills/` check the package,
run and fix the code, draft the report and emails, and build the ZIP. **The reviewer remains
accountable for everything that leaves the team**: the report, every email, and the published
package. This page sets out what the reviewer checks at each step, which evidence to keep, and
the *AI vs. me* table for the package's GitHub issue.

Three rules:

1. **The AI does the work, and a person signs off on it.** Nothing goes to authors, the
   Metadata Editor or the Reproducible Research Repository (RRR) until the reviewer has checked it.
2. **Every AI change is on the record.** Every change to the package is a commit in
   `evidence/package.git`, and every run is timed and hashed. If something isn't in the
   evidence, treat it as not done.
3. **We disclose the use of AI.** Every report carries the *Use of AI* statement (below), and every
   GitHub issue gets the AI use summary.

## The flow

| Step | The AI produces | The reviewer checks before moving on |
|---|---|---|
| 1 Completeness | `completeness_check.md`, `emails/1_*` | Every item marked *Reviewer to confirm*. The verdict. Edit email 1 and send it yourself. |
| 2 Run | `run_log.md`, `evidence/AI_CHANGES.md`, `run_times.csv`, `runN_hashes.csv`, `run_comparison.csv` | Every entry in `AI_CHANGES.md` (see *Checking AI changes*). Two runs with exit code 0 in `run_times.csv`. Run 1 and run 2 identical in `run_comparison.csv`. On the private path, you run the code yourself. |
| 3 Report | `verification_report_[ID].md`/`.tex`, the PDF, `evidence/exhibit_comparison.csv`, `emails/3_*` | Every exhibit that is *not* "Reproduced", checked against the manuscript yourself. At first we will also check "Reproduced" exhibits by eye (we will keep defining these rules as we have more data on AI performance). The *Use of AI* statement is present. Then send email 3. |
| 4 Publication | `step4-…` commits, `[ID].zip`, `zip_check.json`, `[ID]_merge.json` | The `step4-…` diffs (licence, README, removed files). `zip_check.json` matches the last commit. The data descriptions in the merge JSON. |
| 5 Pre-publication | `prepublication_review_[ID].md` | Every PII hit opened and judged by you, not the AI. The JSON issues are fixed in the Metadata Editor. The verdict is *Ready to go live*. |
| AI use summary | `ai_use_summary.md` | Fill in the *AI vs. me* table and the time, and paste it into the GitHub issue. |

If the package does not reproduce, the review stops after step 3: the report goes to the
authors, and the *AI vs. me* table covers steps 1–3 only.

## Checking AI changes

Open `evidence/AI_CHANGES.md`, or view the history in GitHub Desktop (see below). For each commit, ask:

- **Did it change only *how* the code runs** (paths, a missing package, a main script, an
  environment fix)? That is acceptable, and it goes in the report's run steps.
- **Did it change *what* the code computes** (estimation commands, samples, variables, data, or
  outputs written by hand)? That is a red flag. Undo it, or report it to the authors as a change
  they must make. Never publish a package with a silent change to results.
- **Is it flagged ⚠ in `AI_CHANGES.md`?** Read the full diff before accepting it.

Also read `evidence/assumptions.md`. Everything the AI assumed or could not check is listed
there, and each item is either confirmed by you or mentioned in the report.

## The *Use of AI* statement in the report

Each report ends its *Reproduction Environment* list with this bullet (in `create-report/assets/report_template.tex`
and in the Markdown skeleton in `create-report/SKILL.md`):

> **Use of AI**: This review was assisted by AI (Claude Code: Opus 5.5), for checking the
> package for completeness, running and debugging the code, comparing outputs with the
> manuscript, and drafting this report. The verification team reviewed this work and remains
> accountable for this report, including any errors in it.

Do not remove it. Adjust two things only: the model (the one that did the review), and the
list of tasks, dropping any the AI did not do (e.g. on the private path, where the AI does not
run the code).

## Evidence to keep

**Save the whole `report/[ID]/` folder to OneDrive, as it is.** Skill 4 tidies it first
(`track_package.py tidy`, Step 6c, which asks before deleting), so it holds the full record and
nothing else: the ZIP, report, emails, AI use summary and an `evidence/` folder with

| File | Why |
|---|---|
| `package.git/` | Every AI change, with diffs (usually under 1 MB), readable without the package folder |
| `AI_CHANGES.md`, `assumptions.md` | What changed, and what was assumed or not checked |
| `run_times.csv`, `runN_*.log`, `runN_hashes.csv`, `run_comparison.csv` | Proof that each run happened, what it printed, and the only record of binary outputs (`.dta`, `.xlsx`, `.pdf`) |
| `exhibit_comparison.csv` | How each exhibit status in the report was reached |
| `zip_manifest.csv`, `zip_check.json` | Ties the published ZIP to the last commit |

`package/[ID]/` is not needed after that.

## Reading the Git history

The package's history is readable from `evidence/package.git` alone, even after `package/[ID]/`
is deleted:

```bash
G=report/RR_WLD_2026_XXX/evidence/package.git
```

```bash
git --git-dir=$G log --format='%h %an %ad %s' --date=short
```

```bash
git --git-dir=$G diff initial-package..HEAD --stat
```

```bash
git --git-dir=$G show <commit>
```

The first command lists every commit, the second summarises all AI changes, and the third
shows one commit with its note and diff.

**In GitHub Desktop:** while the package folder exists, add `package/[ID]` as a local repository.
Without it, make a throwaway copy, cut its link to the evidence, then add the copy:

```bash
git clone report/RR_WLD_2026_XXX/evidence/package.git ~/Desktop/review_XXX
```

```bash
git -C ~/Desktop/review_XXX remote remove origin
```

Never click **Publish repository**: the review history must never go to GitHub.com. The copy
holds code and text only. Binary outputs are checked through `runN_hashes.csv`.

## AI use summary (GitHub issue)

`ai_use_summary.md` has two parts to fill in and paste into the issue. The AI never fills
them in.

**AI vs. me.** One row for the AI's changes and one per stage (completeness, run, report,
publication) with what the AI found. The pre-publication review is not in the table: the
reviewer does not redo it. Mark *Checked* and *Match* with `y`/`n`; for the AI changes and the
report, use counts (`7 / 9` exhibits checked, `7 / 7` matching). Say in one line what the AI
got wrong. Then answer whether the AI's outputs would have gone out unchanged, and fill in
the time. These tables, across the first reviews, are the benchmark for moving to fully
automated reviews.

```markdown
| Stage | AI result | Checked | Match | What the AI got wrong |
|---|---|---|---|---|
| AI changes | 6 code change(s), 2 flagged | 6 / 6 | 5 / 6 | fix-paths also changed a sample filter |
| 1 Completeness | verdict PROCEED; 23 present, 0 missing | y | y | |
| 2 Run | 2 runs; outputs identical | y | y | |
| 3 Report | 9 exhibits: 7 reproduced, 1 does not reproduce | 9 / 9 | 8 / 9 | Table 3 is a rounding difference |
| 4 Publication | ZIP built correctly, with data needed (no extra or missing files) | y | y | |
```

**Comments.** Open items the script found in the files; add your own.

