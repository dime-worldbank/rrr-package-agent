#!/usr/bin/env python3
"""JSON consistency checks: Metadata Editor JSON vs protocol, vs itself, vs package contents, vs report.

Usage:
    python scripts/check_metadata.py <ID>.json [--package <package root>] [--out report.md]

Standard library only (keeps the script dependency-free). Uses `pdftotext` for the reproducibility report.
Results are PASS / FAIL / WARN / INFO. Every FAIL and WARN must be re-checked by hand.
Check ids (J1.x–J4.x) refer to references/JSON_CHECKS.md.
"""
import argparse, datetime, json, os, re, shutil, subprocess, unicodedata

# ---------------------------------------------------------------- constants (metadata_protocol.md + team practice)
PRODUCER = {"name": "Reproducibility WBG", "abbr": "DECDI",
            "affiliation": "World Bank - Development Impact Department",
            "role": "Verification and preparation of metadata"}
ID_RE = re.compile(r"^(RR|PP|FR)_[A-Z]{3}_20\d{2}_\d+(-v\d+)?$")
OUTPUT_TYPES = {"Working Paper", "Journal Article", "Flagship Report/Dataset", "Flagship Report", "Dataset"}
LICENSES = {"MIT License": "https://opensource.org/license/mit",
            "World Bank IGO Rider": "https://github.com/worldbank/metadata-editor/blob/main/WB-IGO-RIDER.md"}
SCRIPT_NOTES = ["Computational reproducibility verified by the Development Impact Analytics Team, World Bank.",
                "Computational reproducibility verified by Development Impact (DECDI) Analytics team, World Bank."]
REPO = ("Reproducible Research Repository (World Bank)", "https://reproducibility.worldbank.org")
# data_statement template (team standard, matches the report's "Verification Process and Data Handling")
DS_TAIL = "For the source, access type, file location, and citation of each dataset, refer to the Datasets section and the README file."
# access_type sentence -> category
ACCESS_TYPES = {
    "Data is publicly available and included in the reproducibility package.": "open",
    "Data is publicly available but not included in the reproducibility package due to file size constraints.": "open_size",
    "Data is publicly available but does not allow redistribution and is not included in the reproducibility package.": "accessible",
    "Data access requires purchase or human approval and is not included in the reproducibility package.": "limited-access",
    "Data is forthcoming in the World Bank Microdata Library or the World Bank Development Data Hub.": "forthcoming",
    "There is no documented way to access the data, and it is not included in the reproducibility package.": "restricted",
    "Data access was granted directly to the study authors by the data owners/managers. It was obtained with a custom data license that does not allow for redistribution and it is not included in the reproducibility package.": "restricted",
}
TYPE_WORD = {"open": "open", "open_size": "open", "accessible": "accessible", "limited-access": "limited-access",
             "forthcoming": "forthcoming", "restricted": "restricted"}
RANK = {"open": 0, "accessible": 1, "forthcoming": 2, "limited-access": 3, "restricted": 4}
TAG_FOR = {"open": "open data", "accessible": "accessible data", "forthcoming": "forthcoming data",
           "limited-access": "limited-access data", "restricted": "restricted data"}
DATA_TAGS = set(TAG_FOR.values()) | {"synthetic data"}
CODE_TAGS = {"open code", "restricted code", "no code"}
ROR = {"world bank": "https://ror.org/00ae7jd04", "world bank group": "https://ror.org/02md09461",
       "international finance corporation": "https://ror.org/049rm1a24", "ifc": "https://ror.org/049rm1a24",
       "international monetary fund": "https://ror.org/05m4rmw09", "imf": "https://ror.org/05m4rmw09"}
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
DATA_EXT = {".dta", ".sav", ".por", ".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".rds", ".rdata", ".rda",
            ".parquet", ".sas7bdat", ".shp", ".dbf", ".gpkg", ".geojson", ".kml", ".feather"}
PLACEHOLDER = re.compile(r"\[[^\]\n]{0,60}(?:citation|TBD|XX|insert|URL|year)[^\]\n]{0,60}\]|\bTBD\b|\bXXX+\b", re.I)

results = []


def add(check, status, msg):
    results.append((check, status, msg))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.replace("\\", "")).strip().lower()


def canon(s):
    """Accepted wording variants seen in real exports ('and it is not included', 'please refer')."""
    return norm(s).replace("and it is not included", "and is not included").replace("please refer", "refer")


def classify_access(a):
    for k, v in ACCESS_TYPES.items():
        if canon(k) == canon(a):
            return v, True
    n = norm(a)
    for pat, v in (("forthcoming|will be made available|microdata library", "forthcoming"),
                   ("purchase|human approval|limited", "limited-access"),
                   ("granted directly|no documented way|restricted|custom data license", "restricted"),
                   ("does not allow redistribution|personal information|cannot be redistributed", "accessible"),
                   ("size", "open_size"), ("publicly available and included", "open")):
        if re.search(pat, n):
            return v, False
    return None, False


def types_in(text):
    """Data types named in a 'relies on N types of data: a, b and c' sentence."""
    n = norm(text)
    m = re.search(r"relies on (\w+) types? of data:?\s*([^.]*)", n)
    if not m:
        return None, None
    cnt = NUM.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else None)
    body = re.sub(r"\([^)]*\)?", "", m.group(2))  # ignore qualifiers in brackets, e.g. "limited-access (forthcoming to MDL)"
    found = {w for w in ("open", "accessible", "limited-access", "forthcoming", "restricted", "embargoed", "synthetic")
             if re.search(r"\b" + w.replace("-", "[- ]?") + r"\b", body)}
    return cnt, found


def pdf_text(path):
    if not path or not os.path.exists(path) or not shutil.which("pdftotext"):
        return ""
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""


# ---------------------------------------------------------------- J1: JSON fields vs protocol
def check_fields(d, pkg_id_hint):
    doc = d.get("doc_desc", {}) or {}
    pd = d.get("project_desc", {}) or {}
    ts = pd.get("title_statement", {}) or {}
    idno, title = ts.get("idno", ""), ts.get("title", "")

    prods = doc.get("producers") or []
    ok = prods and all(prods[0].get(k) == v for k, v in PRODUCER.items())
    add("J1.1", "PASS" if ok else "FAIL", "producers match protocol" if ok else f"producers differ: {prods}")
    for k, v in (("doc_desc.prod_date", doc.get("prod_date")), ("project_desc.production_date", pd.get("production_date"))):
        good = v and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v))
        add("J1.2", "PASS" if good else "FAIL", f"{k} = {v!r}")
    if str(doc.get("version", "1")) != "1":
        add("J1.2", "INFO", f"version = {doc.get('version')} (ok only for a revised entry)")

    add("J1.3", "PASS" if ID_RE.match(idno) else "FAIL", f"idno {idno!r}" + ("" if ID_RE.match(idno) else " does not match TYPE_ISO3_YEAR_NUMBER"))
    if pkg_id_hint and idno != pkg_id_hint:
        add("J1.3", "FAIL", f"idno {idno} != package folder {pkg_id_hint}")

    outs = pd.get("output") or []
    otitle = outs[0].get("title", "") if outs else ""
    pre = "Reproducibility package for "
    if not title.startswith(pre):
        add("J1.4", "FAIL", f"title should start {pre!r}: {title[:80]!r}")
    elif otitle and norm(title[len(pre):]) != norm(otitle):
        add("J1.4", "WARN", f"title differs from output[0].title:\n    title : {title[len(pre):]}\n    output: {otitle}")
    else:
        add("J1.4", "PASS", "title format ok and matches output title")

    authors = pd.get("authoring_entity") or []
    bad = [(a.get("name"), [k for k in ("name", "affiliation", "email") if not a.get(k)]) for a in authors]
    bad = [b for b in bad if b[1]]
    add("J1.5", "FAIL" if bad or not authors else "PASS", f"authors missing fields: {bad}" if bad else f"{len(authors)} authors complete")

    geos = pd.get("geographic_units") or []
    badg = [g.get("code") for g in geos if not re.fullmatch(r"[A-Z]{3,4}", g.get("code") or "")]
    add("J1.6", "FAIL" if badg or not geos else "PASS", f"geographic codes {[g.get('code') for g in geos]}" + (f" invalid: {badg}" if badg else ""))
    if geos and idno.count("_") >= 2 and idno.split("_")[1] not in [g.get("code") for g in geos]:
        add("J1.6", "WARN", f"idno region/country {idno.split('_')[1]} not in geographic_units")

    ab = pd.get("abstract", "")
    flags = [f for f, p in (("double space", r"  "), ("line-break hyphen", r"\w-\s*\n\s*\w"), ("LaTeX", r"\\[a-z]+\{|\$"), ("newline", r"\n")) if re.search(p, ab)]
    add("J1.7", "FAIL" if not ab else ("WARN" if flags else "PASS"), "abstract empty" if not ab else f"abstract ({len(ab)} chars)" + (f" has {flags}" if flags else ""))
    # JEL ids carry a leading/trailing space by design -> not checked
    add("J1.8", "PASS" if pd.get("keywords") and pd.get("topics") else "WARN", f"{len(pd.get('keywords') or [])} keywords, {len(pd.get('topics') or [])} topics")

    if not outs:
        add("J1.9", "FAIL", "no output entry")
    else:
        ty, desc = outs[0].get("type", ""), outs[0].get("description", "")
        if ty not in OUTPUT_TYPES:
            add("J1.9", "FAIL", f"output type {ty!r} not allowed")
        elif ty == "Working Paper" and "Policy Research Working Paper" not in (desc or ""):
            add("J1.9", "WARN", f"WP description should be 'Policy Research Working Paper (PRWP) ####': {desc!r}")
        elif ty == "Journal Article" and norm(desc) in ("journal article", "journal articles", ""):
            add("J1.9", "WARN", f"Journal Article description should be the journal name, got {desc!r}")
        else:
            add("J1.9", "PASS", f"output {ty!r} / {desc!r}")

    disc = pd.get("disclaimer", "")
    add("J1.10", "PASS" if disc and norm(disc) != "default" else "FAIL", "disclaimer " + ("present" if disc and norm(disc) != "default" else "missing/Default"))
    lic = {l.get("name"): l.get("uri") for l in (pd.get("license") or [])}
    for n, u in LICENSES.items():
        add("J1.11", "PASS" if lic.get(n) == u else "FAIL", f"license {n}" + ("" if lic.get(n) == u else f" missing/wrong (have {lic})"))
    emails = [norm(c.get("email")) for c in pd.get("contacts") or []]
    add("J1.12", "PASS" if "reproducibility@worldbank.org" in emails else "WARN", "contacts " + ("include" if "reproducibility@worldbank.org" in emails else "lack") + " reproducibility@worldbank.org")

    sw = pd.get("software") or []
    if not sw:
        add("J1.13", "FAIL", "no software listed")
    for s in sw:
        add("J1.13", "PASS" if s.get("version") else "FAIL", f"software {s.get('name')} version={s.get('version')!r}")

    scr = (pd.get("scripts") or [{}])[0]
    add("J1.14", "PASS" if scr.get("zip_package") == f"{idno}.zip" else "FAIL", f"scripts.zip_package = {scr.get('zip_package')!r}")
    if norm(scr.get("title")) != norm(title):
        add("J1.14", "WARN", "scripts.title differs from project title")
    if not any(norm(scr.get("notes")) == norm(n) for n in SCRIPT_NOTES):
        add("J1.14", "WARN", f"scripts.notes wording: {scr.get('notes')!r}")
    dep, swn = norm(scr.get("dependencies")), " " + " ".join(norm(s.get("name")) for s in sw) + " "
    for lang, word in (("stata", "ado"), (" r ", "renv"), ("python", "requirements")):
        if lang in swn and word not in dep and not (word == "requirements" and re.search("environment|conda|pyproject", dep)):
            add("J1.14", "WARN", f"dependencies should mention {word!r}: {scr.get('dependencies')!r}")

    repos = pd.get("repository_uri") or []
    ok = repos and repos[0].get("name") == REPO[0] and repos[0].get("uri", "").rstrip("/") == REPO[1]
    add("J1.15", "PASS" if ok else "WARN", "repository_uri" + ("" if ok else f" differs (ok only for DDH/journal): {repos}"))

    ri = pd.get("reproduction_instructions", "")
    st = norm(ri).replace("*", "")
    add("J1.19", "FAIL" if not ri else ("PASS" if st.startswith("to reproduce the findings") else "WARN"),
        "reproduction_instructions " + ("empty" if not ri else ("ok start" if st.startswith("to reproduce the findings") else f"start: {ri[:70]!r}")))
    tr = pd.get("technology_requirements", "")
    add("J1.20", "PASS" if re.search(r"run\s*time|runtime|minutes|hours", tr, re.I) else "WARN", f"technology_requirements = {tr!r}")
    te = pd.get("technology_environment", "")
    if not norm(te).startswith(norm("Paper exhibits were reproduced on a computer with the following specifications:")):
        add("J1.21", "WARN", f"technology_environment start: {te[:70]!r}")
    else:
        miss = [k for k in ("os", "processor", "memory") if not re.search(k, te, re.I)]
        add("J1.21", "WARN" if miss else "PASS", "technology_environment" + (f" missing {miss}" if miss else " ok"))
        sw = [s.get("name") for s in pd.get("software") or [] if s.get("name") and re.search(re.escape(s["name"]), te, re.I)]
        if sw:
            add("J1.21", "WARN", f"technology_environment mentions software {sw}; versions belong only in software")

    dc = d.get("datacite", {}) or {}
    creators = dc.get("creators") or []
    n_fail = 0
    for c in creators:
        who = c.get("name") or f"{c.get('givenName', '')} {c.get('familyName', '')}".strip()
        if c.get("nameType") == "Personal" and not (c.get("givenName") and c.get("familyName")):
            add("J1.22", "FAIL", f"creator {who!r}: Personal without given/family name"); n_fail += 1
        if c.get("nameType") not in ("Personal", "Organizational", "Organization"):
            add("J1.22", "FAIL", f"creator {who!r}: nameType {c.get('nameType')!r}"); n_fail += 1
        for a in c.get("affiliation") or []:
            an = norm(a.get("name"))
            if an in ROR and a.get("affiliationIdentifier") != ROR[an]:
                add("J1.22", "FAIL", f"creator {who!r}: {a.get('name')} ROR should be {ROR[an]}"); n_fail += 1
            if a.get("affiliationIdentifier") and (a.get("affiliationIdentifierScheme") != "ROR" or a.get("schemeUri") != "https://ror.org"):
                add("J1.22", "WARN", f"creator {who!r}: ROR scheme/schemeUri incomplete")
            if not a.get("affiliationIdentifier") and an not in ROR:
                add("J1.22", "INFO", f"creator {who!r}: {a.get('name')!r} has no ROR (blank ok if none exists)")
            if re.search(r";| and ", a.get("name") or ""):
                add("J1.22", "WARN", f"creator {who!r}: several affiliations in one row")
        if not c.get("affiliation"):
            add("J1.22", "WARN", f"creator {who!r}: no affiliation")
    titles = dc.get("titles") or []
    if len(titles) < 2 or norm(titles[0].get("title")) != norm(title) or titles[1].get("title") != idno:
        add("J1.22", "FAIL", f"datacite titles should be [title, idno]: {[t.get('title') for t in titles]}"); n_fail += 1
    for k, v in (("publisher", "World Bank"), ("language", "en")):
        if dc.get(k) != v:
            add("J1.22", "FAIL", f"datacite {k} = {dc.get(k)!r}"); n_fail += 1
    ty = dc.get("types") or {}
    if ty.get("resourceType") != "Reproducibility package" or ty.get("resourceTypeGeneral") != "Other":
        add("J1.22", "FAIL", f"datacite types = {ty}"); n_fail += 1
    want = f"https://reproducibility.worldbank.org/index.php/catalog/study/{idno}"
    if dc.get("url") != want:
        add("J1.22", "FAIL", f"datacite url {dc.get('url')!r} != {want}"); n_fail += 1
    if str(dc.get("publicationYear", "")) != str(datetime.date.today().year):
        add("J1.22", "WARN", f"datacite publicationYear {dc.get('publicationYear')!r}")
    if not n_fail:
        add("J1.22", "PASS", "datacite core fields")
    an_ = [norm(a.get("name")) for a in authors]
    cn = [norm(c.get("name") or f"{c.get('givenName', '')} {c.get('familyName', '')}") for c in creators]
    add("J1.23", "PASS" if an_ == cn else "WARN", "datacite creators = authoring_entity" if an_ == cn else f"creators differ from authors:\n    authors : {an_}\n    creators: {cn}")

    tags = [norm(t.get("tag")) for t in (d.get("tags") or [])]
    dtags = [t for t in tags if t in DATA_TAGS and t != "synthetic data"]
    ctags = [t for t in tags if t in CODE_TAGS]
    add("J1.24", "PASS" if "doi" in tags else "FAIL", "DOI tag" + ("" if "doi" in tags else " missing"))
    add("J1.24", "PASS" if len(dtags) == 1 else "FAIL", f"data access tags {dtags}")
    add("J1.24", "PASS" if len(ctags) == 1 else "FAIL", f"code access tags {ctags}")
    other = [t for t in tags if t not in DATA_TAGS | CODE_TAGS | {"doi"}]
    if other:
        add("J1.24", "WARN", f"unrecognised tags {other}")

    ph = []
    for k in ("data_statement", "reproduction_instructions", "technology_environment", "technology_requirements", "abstract"):
        ph += PLACEHOLDER.findall(str(pd.get(k, "")))
    for ds in pd.get("datasets") or []:
        ph += PLACEHOLDER.findall(" ".join(str(v) for v in ds.values()))
    add("J1.25", "FAIL" if ph else "PASS", f"placeholders left in JSON: {ph[:8]}" if ph else "no placeholders in JSON")
    return idno, pd, dtags


# ---------------------------------------------------------------- J2: datasets, data statement, access logic
def check_data(pd, dtags):
    cats = []
    for i, ds in enumerate(pd.get("datasets") or []):
        nm = (ds.get("name") or f"#{i}").strip()
        if ds.get("name") != nm:
            add("J2.1", "WARN", f"dataset name has leading/trailing space: {ds.get('name')!r}")
        at = ds.get("access_type", "")
        cat, std = classify_access(at)
        cats.append((nm, cat, ds))
        if not std:
            add("J2.1", "FAIL" if not cat else "WARN", f"[{nm}] access_type is not a standard sentence (read as {cat}): {at!r}")
        note = ds.get("note", "")
        if not note:
            add("J2.1", "FAIL", f"[{nm}] note empty")
        else:
            if not re.search(r"access|collected|downloaded|retrieved|(19|20)\d{2}", note, re.I):
                add("J2.1", "WARN", f"[{nm}] note has no access date")
            if not re.search(r"file|folder|location|/|\.\w{2,5}\b", note, re.I):
                add("J2.1", "WARN", f"[{nm}] note has no file location")
        c = ds.get("citation", "")
        if not c:
            add("J2.2", "FAIL", f"[{nm}] citation missing")
        elif re.fullmatch(r"\s*https?://\S+\s*", c):
            add("J2.2", "FAIL", f"[{nm}] citation is only a URL")
        else:
            if "[dataset]" not in c.lower():
                add("J2.2", "WARN", f"[{nm}] citation lacks '[dataset]'")
            if not re.search(r"(19|20)\d{2}", c):
                add("J2.2", "WARN", f"[{nm}] citation has no year")
        if cat in ("open", "open_size", "accessible") and not ds.get("uri") and not re.search(r"https?://", c + note):
            add("J2.2", "WARN", f"[{nm}] public data without any URL")
        if cat in ("restricted", "limited-access") and not ds.get("license"):
            add("J2.2", "WARN", f"[{nm}] restricted/limited data without license")
    if not cats:
        add("J2.1", "FAIL", "no datasets")
    add("J2.1", "INFO", "datasets -> access: " + "; ".join(f"{n} -> {c}" for n, c, _ in cats))

    types = {TYPE_WORD[c] for _, c, _ in cats if c}
    # data_statement template
    stmt = pd.get("data_statement", "")
    n = norm(stmt)
    cnt, named = types_in(stmt)
    if cnt is None:
        add("J2.3", "FAIL", "data_statement does not follow the template "
            "'The reproducibility package relies on N types of data: …. " + DS_TAIL + f"'\n    have: {stmt!r}")
    else:
        if not n.startswith("the reproducibility package relies on"):
            add("J2.3", "WARN", f"data_statement start: {stmt[:60]!r}")
        if norm(DS_TAIL) not in n:
            add("J2.3", "WARN", f"data_statement should end with: {DS_TAIL!r}")
        if cnt != len(named):
            add("J2.3", "FAIL", f"data_statement says {cnt} type(s) but names {sorted(named)}")
        if types and named != types:
            add("J2.4", "FAIL", f"data_statement types {sorted(named)} != dataset access types {sorted(types)}")
        elif types:
            add("J2.4", "PASS", f"data_statement types = dataset access types {sorted(types)}")
        if "\\" in stmt:
            add("J2.3", "WARN", "data_statement contains a stray backslash")
        if not [r for r in results if r[0] == "J2.3" and r[1] != "PASS"]:
            add("J2.3", "PASS", "data_statement follows the template")
    if types:
        top = max(types, key=lambda t: RANK[t])
        if not dtags:
            add("J2.5", "FAIL", f"no data access tag; should be {TAG_FOR[top]!r}")
        elif dtags[0] != TAG_FOR[top]:
            add("J2.5", "FAIL", f"data access tag {dtags[0]!r} but most restrictive dataset is {TAG_FOR[top]!r}")
        else:
            add("J2.5", "PASS", f"data access tag = most restrictive ({TAG_FOR[top]})")
    ri = pd.get("reproduction_instructions", "")
    if types - {"open"} and "access" not in ri.lower():
        add("J2.6", "WARN", "some data is not included but reproduction_instructions don't say how to access it")
    return cats, types


# ---------------------------------------------------------------- J3: JSON vs package contents
def check_package(root, idno, pd, cats):
    files = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), root))
    base = {}
    for f in files:
        base.setdefault(os.path.basename(f).lower(), []).append(f)
    in_pkg = lambda f: not re.search(r"(^|/)(ado|renv|site-packages)/", f)
    data_files = [f for f in files if os.path.splitext(f)[1].lower() in DATA_EXT and in_pkg(f) and "/" in f
                  and not re.search(r"(^|/)(output|outputs|results|tables|figures)/", f, re.I)]
    mentioned = set()
    ext_re = r"(?:dta|csv|tsv|xlsx?|xlsm|sav|rds|rdata|rda|parquet|json|shp|dbf|gpkg|geojson|txt|zip|sas7bdat)"
    names = sorted(base, key=len, reverse=True)
    for nm, cat, ds in cats:
        txt = " ".join(str(ds.get(k, "")) for k in ("note", "name")).replace("\\", "/")
        low = txt.lower()
        # shipped files whose full basename appears in the note (handles spaces in names)
        docs = {"data_hash_report.csv", "variable_inventory.csv", "comparison_report.csv", "license.txt", "wb-igo-rider.txt"}
        found = [base[b][0] for b in names if os.path.splitext(b)[1] in DATA_EXT | {".txt", ".zip", ".json"} and b in low and b not in docs]
        mentioned.update(os.path.basename(f).lower() for f in found)
        toks = set(re.findall(r"[^\s;,:()\"']+\." + ext_re + r"\b", txt, re.I))
        missing = []
        for t in toks:
            b = os.path.basename(t).lower()
            if "*" in b or "[" in b or "{" in b or "<" in b:
                continue
            if not any(os.path.basename(f).lower().endswith(b) for f in found) and b not in base:
                missing.append(b)
        if cat in ("restricted", "limited-access", "accessible", "forthcoming"):
            add("J3.1", "FAIL" if found else "PASS",
                f"[{nm}] is {cat} but these files ARE in the zip: {found}" if found else f"[{nm}] ({cat}): named files not shipped")
        elif cat == "open":
            if missing:
                add("J3.2", "WARN", f"[{nm}] 'included in the package' but not found: {missing[:10]}")
            elif found:
                add("J3.2", "PASS", f"[{nm}] named files present ({len(found)})")
            else:
                add("J3.2", "WARN", f"[{nm}] 'included' but no shipped file is named in the note")
        elif cat == "open_size" and found:
            add("J3.2", "WARN", f"[{nm}] says 'not included due to size' but files are shipped: {found[:5]}")
    unmatched = [f for f in data_files if os.path.basename(f).lower() not in mentioned]
    add("J3.3", "WARN" if unmatched else "PASS",
        f"{len(data_files)} data files shipped; {len(unmatched)} not named in any dataset note" +
        "".join(f"\n    - {u}" for u in unmatched[:40]) + ("\n    …" if len(unmatched) > 40 else ""))

    sw = " " + " ".join(norm(s.get("name")) for s in pd.get("software") or []) + " "
    exts = {os.path.splitext(f)[1].lower() for f in files if in_pkg(f)}
    for lang, ex, key in (("Stata", {".do"}, "stata"), ("R", {".r", ".rmd", ".qmd"}, " r "), ("Python", {".py", ".ipynb"}, "python")):
        if ex & exts and key not in sw:
            add("J3.4", "FAIL", f"package has {sorted(ex & exts)} files but software does not list {lang}")
        if key in sw and not ex & exts:
            add("J3.4", "WARN", f"software lists {lang} but no {lang} scripts in the package")
    if not [r for r in results if r[0] == "J3.4"]:
        add("J3.4", "PASS", "software list matches code languages")

    ri = pd.get("reproduction_instructions", "")
    named = set(re.findall(r"[\w\-./&]+\.(?:do|R|r|py|ipynb|Rmd|qmd|sh|m|jl)\b", ri))
    for n in named:
        b = os.path.basename(n).lower()
        add("J3.5", "PASS" if b in base else "WARN", f"instructions name {n!r}: " + (f"found at {base[b][0]}" if b in base else "NOT in package"))
    m = re.findall(r"line\s+(\d+)\s+of\s+(?:the\s+)?(?:do-?file|script|file)?\s*`?([\w\-. &]+\.(?:do|R|py))", ri, re.I)
    for ln, f in m:
        hit = base.get(os.path.basename(f).lower())
        if hit:
            try:
                line = open(os.path.join(root, hit[0]), errors="ignore").read().splitlines()[int(ln) - 1]
                ok = re.search(r"(?i)(cd |global|setwd|here|root|path|dir|=)", line)
                add("J3.5", "PASS" if ok else "WARN", f"line {ln} of {f}: {line.strip()[:90]!r}")
            except Exception:
                add("J3.5", "WARN", f"line {ln} of {f} does not exist")

    zp = (pd.get("scripts") or [{}])[0].get("zip_package")
    if os.path.basename(os.path.normpath(root)) + ".zip" != zp:
        add("J3.6", "WARN", f"scripts.zip_package {zp!r} vs package folder {os.path.basename(os.path.normpath(root))!r}")
    return files


# ---------------------------------------------------------------- J4: JSON vs reproducibility report
def check_report(root, idno, pd, types, report=None):
    rp = report or os.path.join(root, f"reproducibility_report_{idno}.pdf")
    if not os.path.exists(rp) and root:
        c = [f for f in os.listdir(root) if f.lower().startswith("reproducibility_report") and f.endswith(".pdf")]
        rp = os.path.join(root, c[0]) if c else None
    text = pdf_text(rp)
    if not text:
        add("J4.1", "WARN", "reproducibility report missing or unreadable; J4 checks skipped")
        return
    flat = re.sub(r"\s+", " ", text)
    cnt, named = types_in(flat)
    jc, jn = types_in(pd.get("data_statement", ""))
    if cnt is None:
        add("J4.1", "WARN", "report has no 'relies on N types of data' line")
    else:
        add("J4.1", "PASS" if named == jn else "FAIL",
            f"data types: report {sorted(named)} vs JSON data_statement {sorted(jn) if jn else None}")
        if jc is not None and cnt != jc:
            add("J4.1", "FAIL", f"report says {cnt} types of data, JSON data_statement says {jc}")
        if cnt != len(named):
            add("J4.1", "WARN", f"report says {cnt} types but names {sorted(named)}; read the sentence")
        if types and named != types:
            add("J4.1", "FAIL", f"report types {sorted(named)} != JSON dataset access types {sorted(types)}")
    for s in pd.get("software") or []:
        v = str(s.get("version", ""))
        if v:
            add("J4.2", "PASS" if v in flat else "WARN", f"{s.get('name')} {v} " + ("in report" if v in flat else "NOT in report"))
    te = pd.get("technology_environment", "")
    for key in ("OS", "Processor", "Memory"):
        m = re.search(key + r"[^:\n]*:\s*([^\n•]+)", te, re.I)
        if m:
            val = m.group(1).strip()[:40]
            ok = norm(val)[:20] in norm(flat)
            add("J4.3", "PASS" if ok else "WARN", f"{key} {val!r} " + ("in report" if ok else "NOT in report"))
    rt = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)", pd.get("technology_requirements", ""), re.I)
    rr = re.search(r"(?:takes|run\s*time|runtime)[^.]{0,40}?(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)", flat, re.I)
    if rt and rr:
        same = rt.group(1) == rr.group(1) and rt.group(2)[0].lower() == rr.group(2)[0].lower()
        add("J4.4", "PASS" if same else "WARN", f"run time JSON {rt.group(0)!r} vs report {rr.group(0)!r}")
    else:
        add("J4.4", "INFO", f"run time JSON={rt.group(0) if rt else '?'} report={rr.group(0) if rr else '?'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--package")
    ap.add_argument("--report", help="reproducibility report PDF (default: <package>/reproducibility_report_<ID>.pdf)")
    ap.add_argument("--out")
    a = ap.parse_args()
    d = json.load(open(a.json, encoding="utf-8"))
    hint = os.path.basename(os.path.normpath(a.package)) if a.package else None
    hint = hint if hint and ID_RE.match(hint) else None
    idno, pd, dtags = check_fields(d, hint)
    cats, types = check_data(pd, dtags)
    if a.package:
        check_package(a.package, idno, pd, cats)
        check_report(a.package, idno, pd, types, a.report)
    elif a.report:
        check_report(None, idno, pd, types, a.report)
    order = ["FAIL", "WARN", "INFO", "PASS"]
    key = lambda r: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r[0])]
    L = [f"# JSON consistency checks: {idno}", "", f"JSON: `{a.json}`  ", f"Package: `{a.package or '(not given)'}`  ",
         f"Run: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
         "Counts: " + ", ".join(f"{k} {sum(1 for r in results if r[1] == k)}" for k in order), "",
         "Re-check every FAIL/WARN by hand. Ids refer to references/JSON_CHECKS.md.", ""]
    for st in order:
        rs = sorted([r for r in results if r[1] == st], key=key)
        if rs:
            L += [f"## {st}"] + [f"- **{c}** {m}" for c, _, m in rs] + [""]
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w").write("\n".join(L))
        print("wrote", a.out)
    print(L[6])
    for r in sorted(results, key=key):
        if r[1] in ("FAIL", "WARN"):
            print(f"{r[1]:5} {r[0]:6} {r[2].splitlines()[0][:160]}")


if __name__ == "__main__":
    main()
