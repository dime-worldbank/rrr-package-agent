#!/usr/bin/env python3
"""First-pass PII scan of code, logs, notebooks and documents (Part A, steps 1 and 5).

Usage: python scripts/scan_code.py "<package root>" --out report/<ID>/prepub/_scans/code_scan.md

Looks for: emails, phone numbers, national IDs, staff UPIs/user paths, hard-coded respondent
lookups (replace id = ... if email/phone/name == ...), name/phone/email variables in code,
notebooks with stored outputs, logs, hidden files and .git history. All evidence is masked.
Third-party ado/renv/site-packages files are skipped, except that emails there are counted.
"""
import argparse, os, re, shutil, subprocess

CODE_EXT = {".do", ".ado", ".r", ".rmd", ".qmd", ".py", ".ipynb", ".sas", ".sps", ".m", ".jl", ".sh", ".tex",
            ".md", ".txt", ".log", ".smcl", ".html", ".json", ".yml", ".yaml", ".csv"}
SKIP_DIRS = re.compile(r"(^|/)(ado|renv|site-packages|node_modules|\.git)(/|$)")
DOC_EXT = {".pdf", ".docx", ".doc", ".pptx", ".xlsx"}
PATS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?<![\w.])(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?)?\d{3,4}[ -]?\d{4}(?![\w.])",
    "curp_mx": r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b",
    "cnic_pk": r"\b\d{5}-\d{7}-\d\b",
    "upi_path": r"(?i)[a-z]:[\\/]+users[\\/]+(wb\d{5,7}|[a-z]\d{5,7})|/Users/[A-Za-z0-9._-]+|OneDrive - (WBG|World Bank)",
}
LOOKUP = re.compile(r"""(?i)\b(replace|gen|generate|mutate|ifelse|case_when|loc|where|filter)\b.{0,120}
    (email|correo|mail|phone|tel|cel|mobile|name|nombre|apellido|curp|cnic|address|direcc)\w*\s*(==|%in%|=|\.eq|\.isin)\s*["'(]""", re.X)
IDCORR = re.compile(r"""(?i)\b(replace|drop|keep|list|br(owse)?)\b.{0,80}\b\w*(id|folio|hhid|caseid|uuid|key)\w*\s*==\s*"?\d{6,}""")
PIIVARS = re.compile(r"(?i)\b(firstname|lastname|first_name|last_name|full_?name|nombre\w*|apellido\w*|phone\w*|telefono\w*|celular\w*|mobile\w*|email\w*|correo\w*|RecipientEmail|IPAddress|LocationLatitude|LocationLongitude|gps\w*|latitude|longitude|curp|cnic|aadhaar|dob|fecha_?nac\w*|address\w*|direccion\w*)\b")


def mask(s):
    s = s.strip()
    if "@" in s:
        u, dmn = s.split("@", 1)
        return u[:1] + "*" * max(len(u) - 1, 1) + "@" + dmn
    return re.sub(r"(?<=\w)\w", "*", s) if not s.isdigit() else s[:2] + "*" * (len(s) - 2)


def is_public_email(e):
    e = e.lower()
    return e.endswith(("@worldbank.org", "@ifc.org", "@imf.org")) or e in {"reproducibility@worldbank.org"} or \
        re.search(r"@(example|domain|email)\.(com|org)$", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out")
    a = ap.parse_args()
    root = os.path.normpath(a.root)
    L = [f"# Code / document PII scan: `{root}`", ""]
    hidden, gits, logs, nbs, docs, archives = [], [], [], [], [], []
    third_party_emails = 0
    hits = {}  # file -> list of (line, kind, masked)
    for dp, dn, fn in os.walk(root):
        rel_dp = os.path.relpath(dp, root)
        if ".git" in dn:
            gits.append(os.path.join(rel_dp, ".git"))
        for f in fn + [d + "/" for d in dn]:
            rel = os.path.normpath(os.path.join(rel_dp, f))
            b = os.path.basename(f.rstrip("/"))
            if b.startswith((".", "~$")) and b not in (".gitkeep",) or b in ("__MACOSX", "Thumbs.db"):
                hidden.append(rel)
        for f in fn:
            rel = os.path.normpath(os.path.join(rel_dp, f))
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(dp, f)
            if ext in (".log", ".smcl") or f == ".Rhistory":
                logs.append(rel)
            if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
                archives.append(rel)
            if ext in DOC_EXT:
                docs.append(rel)
            if ext not in CODE_EXT and f != ".Rhistory":
                continue
            if ext == ".csv" and os.path.getsize(full) > 2_000_000:
                continue  # data, handled by scan_data.R
            try:
                text = open(full, errors="ignore").read()
            except Exception:
                continue
            if SKIP_DIRS.search(rel.replace(os.sep, "/")):
                third_party_emails += len(re.findall(PATS["email"], text))
                continue
            if ext == ".ipynb" and re.search(r'"outputs":\s*\[\s*\{', text):
                nbs.append(rel)
            for i, line in enumerate(text.splitlines(), 1):
                found = []
                for k, p in PATS.items():
                    for m in re.finditer(p, line):
                        v = m.group(0)
                        if k == "email" and is_public_email(v):
                            continue
                        if k == "phone" and (re.fullmatch(r"(19|20)\d{2}[ -]?\d{4}", v.strip()) or len(re.sub(r"\D", "", v)) < 10):
                            continue
                        found.append((k, mask(v)))
                if LOOKUP.search(line):
                    found.append(("respondent_lookup", mask(line[:90])))
                elif IDCORR.search(line):
                    found.append(("hardcoded_id", re.sub(r"\d{4,}", lambda m: m.group(0)[:2] + "*" * (len(m.group(0)) - 2), line.strip()[:100])))
                if PIIVARS.search(line) and ext in (".do", ".r", ".rmd", ".qmd", ".py", ".ipynb", ".sas", ".sps"):
                    found.append(("pii_varname", ",".join(sorted(set(m.group(0) for m in PIIVARS.finditer(line))))[:80]))
                if found:
                    hits.setdefault(rel, []).append((i, found))

    L.append("## Hidden content")
    L.append(f"- `.git` folders: {gits or 'none'}")
    for g in gits:
        gd = os.path.join(root, g)
        if shutil.which("git"):
            r = subprocess.run(["git", "--git-dir", gd, "log", "--all", "--oneline"], capture_output=True, text=True)
            L.append(f"  - `{g}`: {len(r.stdout.splitlines())} commits. Run `git ls-tree -r` on each commit and compare with the working tree (Part A step 1)")
            r2 = subprocess.run(["git", "--git-dir", gd, "log", "--all", "--diff-filter=D", "--name-only", "--format="], capture_output=True, text=True)
            dl = sorted(set(x for x in r2.stdout.splitlines() if x))
            L.append(f"  - files deleted in history (still shipped in .git): {len(dl)}" + "".join(f"\n    - {x}" for x in dl[:40]))
            r3 = subprocess.run(["git", "--git-dir", gd, "log", "--all", "--format=%ae"], capture_output=True, text=True)
            ae = sorted(set(r3.stdout.split()))
            L.append(f"  - commit author emails: {[mask(x) for x in ae]}")
    L.append(f"- hidden/system files: {len(hidden)}" + "".join(f"\n  - {h}" for h in hidden[:30]))
    L.append(f"- logs / histories (may print data): {logs or 'none'}")
    L.append(f"- notebooks with stored outputs (read the outputs): {nbs or 'none'}")
    L.append(f"- nested archives (unpack + review): {archives or 'none'}")
    L.append(f"- documents to open by hand (PDF/Office): {len(docs)}" + "".join(f"\n  - {d}" for d in docs[:40]))
    L.append(f"- emails inside third-party ado/renv packages (normally package authors, ignore): {third_party_emails}")
    L.append("")
    L.append("## Hits in code / text (masked)")
    if not hits:
        L.append("None.")
    kinds_total = {}
    for f, rows in sorted(hits.items()):
        kinds = {}
        for _, fl in rows:
            for k, _ in fl:
                kinds[k] = kinds.get(k, 0) + 1
                kinds_total[k] = kinds_total.get(k, 0) + 1
        L.append(f"\n### `{f}`: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
        shown = 0
        for i, fl in rows:
            if all(k == "pii_varname" for k, _ in fl) and shown > 15:
                continue
            L.append(f"- L{i}: " + "; ".join(f"{k}: `{v}`" for k, v in fl))
            shown += 1
            if shown >= 60:
                L.append(f"- … {len(rows) - shown} more lines")
                break
    L.insert(2, "Totals: " + (", ".join(f"{k} {n}" for k, n in sorted(kinds_total.items())) or "no hits") +
             ". `pii_varname` alone is usually fine (code that drops/renames PII). Check `email`, `phone`, "
             "`respondent_lookup` and `hardcoded_id` by hand.\n")
    txt = "\n".join(L)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w").write(txt)
        print("wrote", a.out)
    print(L[2])


if __name__ == "__main__":
    main()
