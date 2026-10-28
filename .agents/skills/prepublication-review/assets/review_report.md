# Pre-publication check: <ID>

<Paper title>. Date: <YYYY-MM-DD>.

**Verdict:** Ready to go live | Fix JSON, then go live | Hold: PII | Hold: data shipped
**PII:** No PII found | No PII found (borderline) | PII found (High / Medium / Low)

## Changes
| # | what to change | where | change to / action | level | who |
|---|---|---|---|---|---|
| 1 | <one short line: the problem> | <file + lines/variable, or JSON field> | <exact new value, or the exact action> | PII High / Data / Fix / Minor | team / authors |

<!--
Rules for this report:
- Only the header, the verdict/PII lines and the Changes table. No summary paragraph, no "checked and not PII" list,
  no list of passed checks, no "not in scope" notes.
- One row per change. Order: PII and shipped data first, then Fix, then Minor. "who" = team (Metadata Editor / re-zip) or authors.
- PII rows: mask the evidence in the "what" cell (M***** A**), give n affected.
- "change to" must be something the team can paste or do: the full new field value, or e.g. "Delete Data/Intermediate/x.dta; re-zip".
- Keep cells short. Evidence goes in "what" only if needed to find the problem (e.g. "says line 18; path is on line 17").
- No changes at all: write "No changes." in place of the table.
- Add a single line `**Not checked:** …` under the table only if something was not opened or only sampled AND it could
  hide PII or change the verdict. Otherwise leave it out.
-->
