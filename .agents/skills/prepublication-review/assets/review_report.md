# Pre-publication check: <ID>

<Paper title>. Date: <YYYY-MM-DD>.

**Verdict:** Ready to go live | Fix JSON, then go live | Hold: PII | Hold: data shipped
**PII:** No PII found | No PII found (borderline) | PII found (High / Medium / Low)
**ZIP SHA-256:** <sha256 of the ZIP reviewed> (matches Skill 4's zip_check.json: yes / no / not found)

## Changes
- <the problem, in one short line>: `<file + lines/variable, or JSON field>`. <The exact new value, or the exact action.>

<!--
Rules for this report:
- Only the header, the verdict/PII/ZIP lines and the Changes list. No summary paragraph, no "checked and not PII" list,
  no list of passed checks, no "not in scope" notes.
- A bullet list, one bullet per change: problem, where, what to change it to. No table, no severity level and no owner.
- Order: PII and shipped data first, then what must be corrected before going live, then wording/format.
- PII bullets: mask the evidence (M***** A**), give n affected.
- The change must be something the team can paste or do: the full new field value, or e.g. "Delete Data/Intermediate/x.dta; re-zip".
  If only the authors can make it (a data or code change), say so in the action ("Ask the authors to …").
- Keep bullets short. Add evidence only if it is needed to find the problem (e.g. "says line 18; path is on line 17").
- No changes at all: write "No changes." in place of the list.
- Add a single line `**Not checked:** …` under the list only if something was not opened or only sampled AND it could
  hide PII or change the verdict. Otherwise leave it out.
-->
