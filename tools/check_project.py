"""
Automatic project check - run this before handing the project in.

It verifies the project structure, looks for leaked secrets, compiles every Python
script, checks that the key data files have the expected size, and lists the items
that are still open. The result is printed AND written to docs/CHECK_REPORT.md.

Usage (from the project root):

    python tools/check_project.py            # offline checks (no keys, no internet)
    python tools/check_project.py --live     # + check .env keys and a running Qdrant

Exit code: 0 = no FAIL, 1 = at least one FAIL.

Status meaning:
    PASS  everything fine
    WARN  not an error, but you should look at it (usually an open to-do)
    FAIL  must be fixed before submitting
    SKIP  could not be checked (e.g. a library is missing)
"""

import argparse
import datetime as dt
import json
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "CHECK_REPORT.md"

# --------------------------------------------------------------------------- #
# Expected values (from the report)
# --------------------------------------------------------------------------- #
EXPECTED_TAXONOMY_NODES = 60          # report 5.2.4
EXPECTED_KB_ISSUES = 308              # 80 % of 385
EXPECTED_KB_PRIVACY = 19
EXPECTED_TEST_ISSUES = 77             # 20 % of 385
EXPECTED_CONFIGS = 12                 # 3 embedding models x 4 chat models
MAX_FILE_MB = 25

REQUIRED_PATHS = [
    "README.md", "requirements.txt", ".env.example", ".gitignore", "docker-compose.yml",
    "docs/SETUP_QDRANT.md", "docs/SETUP_N8N.md", "data/README.md",
    "01_keywords/Keyword_domain.md", "01_keywords/keyword_generation_prompt.md",
    "02_collect_repositories/1_find_repositories.py",
    "03_collect_issues/1_get_issues.py",
    "04_annotation/1_random_sample_issues.py", "04_annotation/3_percent_agreement.py",
    "project_env.py", "tools/make_submission_zip.py",
    "05_rag_pipeline/config.py", "05_rag_pipeline/build_taxonomy_index.py",
    "05_rag_pipeline/build_ground_truth_index.py",
    "05_rag_pipeline/prompts/identification_prompt.md",
    "05_rag_pipeline/data/PbD Issues Taxonomy.json", "05_rag_pipeline/data/Ground_data.json",
    "06_evaluation/recall_at_k.py", "06_evaluation/Testset.xlsx",
    "06_evaluation/Summary_Averages.txt",
]

SECRET_PATTERNS = {
    "OpenAI key": r"sk-(proj-)?[A-Za-z0-9_-]{20,}",
    "Anthropic key": r"sk-ant-[A-Za-z0-9_-]{20,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{30,}",
    "GitHub token": r"(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}",
    "JWT / Qdrant key": r"eyJhbGciOi[A-Za-z0-9_.-]{20,}",
    "Private key block": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Hardcoded key assignment": r"""(?i)(api[_-]?key|secret|token)\s*[=:]\s*["'][A-Za-z0-9_\-]{24,}["']""",
}
FORBIDDEN_FILES = ["*.pem", "*.key", "*.p12", "*.pfx", "App.env", "id_rsa*"]   # .env is allowed locally (see below)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".csv", ".env", ".example",
                 ".toml", ".cfg", ".ini", ".sh", ""}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "qdrant_storage", "n8n_data", "_n8n_export_all", "dist"}
LOCAL_SECRET_FILES = {".env"}   # your real keys - allowed on your machine, never scanned or shipped

results = []  # (status, area, check, detail)


def add(status, area, check, detail=""):
    results.append((status, area, check, detail))


def files(pattern="*"):
    for p in ROOT.rglob(pattern):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def check_structure():
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    if missing:
        add("FAIL", "Structure", "Required files present", "Missing: " + ", ".join(missing))
    else:
        add("PASS", "Structure", "Required files present", f"{len(REQUIRED_PATHS)} files found")


def check_secrets():
    bad_names = [str(p.relative_to(ROOT)) for pat in FORBIDDEN_FILES for p in files(pat)]
    if bad_names:
        add("FAIL", "Secrets", "No key / credential files", "Remove: " + ", ".join(sorted(set(bad_names))))
    else:
        add("PASS", "Secrets", "No key / credential files", "no .pem / .key / App.env found")

    hits = []
    scanned = 0
    for p in files():
        if p.suffix.lower() not in TEXT_SUFFIXES or p.stat().st_size > 5_000_000:
            continue
        if p.name in ("check_project.py", "make_submission_zip.py"):   # these contain the patterns themselves
            continue
        if p.name in LOCAL_SECRET_FILES or (p.name.startswith(".env.") and p.name != ".env.example"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for name, pat in SECRET_PATTERNS.items():
            if re.search(pat, text):
                hits.append(f"{p.relative_to(ROOT)} ({name})")
    if hits:
        add("FAIL", "Secrets", "No API keys inside files", "Found in: " + "; ".join(hits[:15]))
    else:
        add("PASS", "Secrets", "No API keys inside files", f"{scanned} text files scanned")

    # .env: may exist locally, but must be git-ignored and is left out of the submission zip
    env = ROOT / ".env"
    if env.exists():
        add("PASS", "Secrets", "Local .env file", ".env exists (your keys) - git-ignored and excluded by tools/make_submission_zip.py; never send it")
    else:
        add("WARN", "Secrets", "Local .env file", "not created yet - copy .env.example to .env and put your NEW keys there")

    # .env.example must stay an empty template
    ex = ROOT / ".env.example"
    filled = []
    if ex.exists():
        for line in ex.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip() and not v.strip().startswith(("http", "<")):
                    filled.append(k.strip())
    add("FAIL" if filled else "PASS", "Secrets", ".env.example has no real values",
        "filled in: " + ", ".join(filled) if filled else "template is empty")

    # every script must read keys through project_env.get_secret()
    direct = []
    for p in files("*.py"):
        if p.name in ("project_env.py", "check_project.py", "make_submission_zip.py"):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if re.search(r"(os\.getenv|os\.environ)[^\n]*(KEY|TOKEN|SECRET|PASSWORD)", line) or re.search(r"load_dotenv\(", line):
                direct.append(f"{p.relative_to(ROOT)}:{i}")
    add("FAIL" if direct else "PASS", "Secrets", "Keys are read only via project_env.get_secret()",
        "reads keys directly: " + ", ".join(direct) if direct else "all scripts use project_env")

    gi = (ROOT / ".gitignore")
    needed = [".env", "*.pem"]
    if gi.exists() and all(n in gi.read_text(encoding="utf-8") for n in needed):
        add("PASS", "Secrets", ".gitignore protects secrets", ".env and *.pem are ignored")
    else:
        add("FAIL", "Secrets", ".gitignore protects secrets", "Add .env and *.pem to .gitignore")


def check_public_release():
    """The project is published - no personal paths, account IDs or hidden Office metadata paths.

    Research data (GitHub issue texts) legitimately contains other people's paths, so text files are
    checked only if they are code / docs / n8n workflows, and Office files only in their metadata.
    """
    import zipfile
    personal = re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}(?!<|YOUR_)[A-Za-z0-9._-]+\\{1,2}")
    onedrive = re.compile(r"d\.docs\.live\.net/[0-9a-f]{8,}")
    code_suffixes = {".py", ".md", ".yml", ".yaml", ".example", ".toml", ".cfg", ".ini", ".sh", ".bat", ".ps1"}
    hits = []
    for p in files():
        rel = p.relative_to(ROOT)
        if p.name in ("check_project.py", "make_submission_zip.py", "CHECK_REPORT.md") or p.name in LOCAL_SECRET_FILES:
            continue
        suf = p.suffix.lower()
        if suf in (".xlsx", ".xlsm", ".docx", ".pptx"):
            try:
                with zipfile.ZipFile(p) as z:
                    meta = b"".join(z.read(n) for n in z.namelist()
                                    if n in ("xl/workbook.xml", "word/settings.xml") or n.startswith("docProps/"))
            except zipfile.BadZipFile:
                continue
            if b"absPath" in meta or b"docs.live.net" in meta or re.search(rb"[A-Za-z]:\\{1,2}Users\\{1,2}(?!<|YOUR_)", meta):
                hits.append(f"{rel} (hidden path in Office metadata)")
        elif suf in code_suffixes or (suf == ".json" and "n8n" in rel.parts):
            t = p.read_text(encoding="utf-8", errors="ignore")
            if personal.search(t):
                hits.append(f"{rel} (personal Windows path)")
            if onedrive.search(t):
                hits.append(f"{rel} (OneDrive account path)")
    add("FAIL" if hits else "PASS", "Secrets", "Public release: no personal paths / account IDs",
        "; ".join(hits[:10]) if hits else "no user names, OneDrive IDs or hidden Office paths in code, docs, workflows or file metadata")


def check_python():
    bad, total = [], 0
    for p in files("*.py"):
        total += 1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                py_compile.compile(str(p), cfile=os.path.join(tmp, "x.pyc"), doraise=True)
        except py_compile.PyCompileError as exc:
            bad.append(f"{p.relative_to(ROOT)}: {exc.msg.strip().splitlines()[-1]}")
    add("FAIL" if bad else "PASS", "Code", "All Python files compile",
        "; ".join(bad) if bad else f"{total} files OK")

    no_doc = []
    for p in files("*.py"):
        rel = p.relative_to(ROOT)
        if rel.parts[0][:2].isdigit() or rel.parts[0] == "tools":
            if not p.read_text(encoding="utf-8", errors="ignore").lstrip().startswith(('"""', "'''")):
                no_doc.append(str(rel))
    add("WARN" if no_doc else "PASS", "Code", "Every script has a header docstring",
        ", ".join(no_doc) if no_doc else "all scripts documented")


def check_data():
    # taxonomy
    try:
        tax = json.loads((ROOT / "05_rag_pipeline/data/PbD Issues Taxonomy.json").read_text(encoding="utf-8"))

        def count(node):
            n = 0
            for v in node.values():
                if isinstance(v, dict):
                    n += 1 if "label" in v else count(v)
            return n

        n = count(tax["root"])
        add("PASS" if n == EXPECTED_TAXONOMY_NODES else "FAIL", "Data", "Taxonomy size",
            f"{n} sub-categories (expected {EXPECTED_TAXONOMY_NODES})")
    except Exception as exc:
        add("FAIL", "Data", "Taxonomy readable", str(exc))

    # ground truth
    try:
        gt = json.loads((ROOT / "05_rag_pipeline/data/Ground_data.json").read_text(encoding="utf-8"))
        priv = sum(1 for it in gt if any(v is True for k, v in it.items() if k and k[0].isdigit()))
        ok = len(gt) == EXPECTED_KB_ISSUES and priv == EXPECTED_KB_PRIVACY
        add("PASS" if ok else "FAIL", "Data", "Knowledge base (80 %)",
            f"{len(gt)} issues, {priv} privacy-related (expected {EXPECTED_KB_ISSUES} / {EXPECTED_KB_PRIVACY})")
    except Exception as exc:
        add("FAIL", "Data", "Ground_data.json readable", str(exc))

    # test set + results (need pandas)
    try:
        import pandas as pd
    except ImportError:
        add("SKIP", "Data", "Test set size", "pandas not installed (pip install -r requirements.txt)")
        pd = None
    if pd is not None:
        try:
            df = pd.read_excel(ROOT / "06_evaluation/Testset.xlsx", header=6).dropna(how="all")
            add("PASS" if len(df) == EXPECTED_TEST_ISSUES else "FAIL", "Data", "Test set (20 %)",
                f"{len(df)} issues (expected {EXPECTED_TEST_ISSUES})")
        except Exception as exc:
            add("FAIL", "Data", "Testset.xlsx readable", str(exc))

    n_out = len(list((ROOT / "06_evaluation/earlier_experiment/LLM_result_data").glob("*.xlsx")))
    n_rec = len(list((ROOT / "06_evaluation/EVA_RECALL").glob("*.xlsx")))
    add("PASS" if n_rec == EXPECTED_CONFIGS else "WARN", "Data", "Recall results for all configurations",
        f"{n_rec} Recall@K files in EVA_RECALL (expected {EXPECTED_CONFIGS}); {n_out} raw model-output files "
        f"in earlier_experiment/ (local only, not published)")

    summ = ROOT / "06_evaluation/Summary_Averages.txt"
    rows = [l for l in summ.read_text(encoding="utf-8").splitlines() if l.startswith("Embedding_")] if summ.exists() else []
    add("PASS" if len(rows) == EXPECTED_CONFIGS else "FAIL", "Data", "Summary_Averages.txt",
        f"{len(rows)} configurations (expected {EXPECTED_CONFIGS})")

    best = None
    for r in rows:
        cells = [c.strip() for c in r.split("|")]
        try:
            r1 = float(cells[1])
        except (IndexError, ValueError):
            continue
        if best is None or r1 > best[1]:
            best = (cells[0], r1)
    if best:
        ok = abs(best[1] - 0.8701) < 1e-4
        add("PASS" if ok else "FAIL", "Data", "Best Recall@1 matches the report (87.01 %)",
            f"{best[0]} = {best[1]*100:.2f} %")


def check_open_items():
    n8n = sorted((ROOT / "05_rag_pipeline/n8n").glob("*_Recall@K.json"))
    dirty = []
    for wf in n8n:
        try:
            d = json.loads(wf.read_text(encoding="utf-8"))
        except Exception:
            dirty.append(f"{wf.name} (invalid JSON)")
            continue
        if d.get("pinData"):
            dirty.append(f"{wf.name} (pinned data)")
        if d.get("shared") or re.search(r"[\w.+-]+@(hotmail|gmail|outlook|yahoo|mahidol)\.", json.dumps(d)):
            dirty.append(f"{wf.name} (owner / e-mail)")
        if "cloud.qdrant.io" in json.dumps(d):
            dirty.append(f"{wf.name} (Qdrant Cloud URL)")
    if not n8n:
        add("WARN", "To-do", "n8n workflows present", "No *_Recall@K.json in 05_rag_pipeline/n8n/ - export your workflows")
    else:
        add("PASS" if len(n8n) == EXPECTED_CONFIGS else "WARN", "To-do", "n8n workflows present",
            f"{len(n8n)} *_Recall@K workflows (expected {EXPECTED_CONFIGS})")
        add("FAIL" if dirty else "PASS", "Secrets", "n8n workflows are clean",
            "; ".join(dirty) if dirty else "no pinned data, owner e-mail or cloud URL")

    tmp = ROOT / "_n8n_export_all"
    if tmp.exists():
        add("WARN", "Hygiene", "Temporary n8n export folder removed", "_n8n_export_all/ still exists - delete it before submitting")

    ddoc = (ROOT / "data/README.md").read_text(encoding="utf-8") if (ROOT / "data/README.md").exists() else ""
    add("WARN" if "TODO" in ddoc else "PASS", "To-do", "Link for the large raw data",
        "data/README.md still contains TODO" if "TODO" in ddoc else "link added")

    raw = ROOT / "data" / "raw"
    local_raw = raw.exists() and any(raw.rglob("*.csv"))
    linked = "drive.google.com" in ddoc or "http" in ddoc.split("Where to get the large files")[-1]
    add("PASS" if (local_raw or linked) else "WARN", "To-do", "Raw data available",
        "local copy in data/raw/" if local_raw else ("linked in data/README.md (Google Drive)" if linked else "no local copy and no link"))

    wanted = {
        "UMAP / centroid keyword script (Fig 5.2-5.3)": "umap",
    }
    names = [p.name.lower() for p in files("*.py") if p.name != "check_project.py"]
    missing = [label for label, key in wanted.items() if not any(key in n for n in names)]
    add("WARN" if missing else "PASS", "To-do", "Scripts that were missing from the original files",
        "still missing: " + ", ".join(missing) if missing else "all present")


def check_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    broken = []
    for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s#]+)", readme):
        if not (ROOT / target).exists():
            broken.append(target)
    for md in ["docs/SETUP_QDRANT.md", "docs/SETUP_N8N.md", "05_rag_pipeline/n8n/README.md", "data/README.md"]:
        f = ROOT / md
        if f.exists():
            for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s#]+)", f.read_text(encoding="utf-8")):
                if not (f.parent / target).resolve().exists():
                    broken.append(f"{md} -> {target}")
    add("FAIL" if broken else "PASS", "Docs", "Relative links in the .md files work",
        ", ".join(broken) if broken else "all links resolve")

    for ph in ["<your", "TODO", "FIXME", "XXX"]:
        if ph in readme:
            add("WARN", "Docs", f"README contains '{ph}'", "finish or remove it")
            break
    else:
        add("PASS", "Docs", "README has no unfinished markers", "")

    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    need = ["pandas", "requests", "qdrant-client", "openai", "cohere", "google-genai", "python-dotenv", "langdetect"]
    miss = [n for n in need if n not in req]
    add("FAIL" if miss else "PASS", "Docs", "requirements.txt lists the main libraries",
        "missing: " + ", ".join(miss) if miss else "ok")


def check_hygiene():
    big = [f"{p.relative_to(ROOT)} ({p.stat().st_size/1e6:.0f} MB)" for p in files()
           if p.stat().st_size > MAX_FILE_MB * 1e6]
    add("WARN" if big else "PASS", "Hygiene", f"No file larger than {MAX_FILE_MB} MB", ", ".join(big) if big else "ok")
    junk = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.name in {".DS_Store", "Thumbs.db"} or p.name.endswith(".pyc")]
    add("WARN" if junk else "PASS", "Hygiene", "No .DS_Store / .pyc leftovers", ", ".join(junk[:10]) if junk else "ok")
    total = sum(p.stat().st_size for p in files())
    add("PASS" if total < 100e6 else "WARN", "Hygiene", "Total project size", f"{total/1e6:.1f} MB")


def check_live():
    env = ROOT / ".env"
    if not env.exists():
        add("WARN", "Live", ".env file", "not created yet (copy .env.example to .env)")
        values = {}
    else:
        values = {}
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
        for k in ["GITHUB_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY", "COHERE_API_KEY"]:
            add("PASS" if values.get(k) else "WARN", "Live", f".env has {k}",
                "set" if values.get(k) else "empty (only needed for the step that uses it)")

    url = values.get("QDRANT_URL") or "http://localhost:6333"
    try:
        import requests
        headers = {"api-key": values["QDRANT_API_KEY"]} if values.get("QDRANT_API_KEY") else {}
        r = requests.get(url.rstrip("/") + "/collections", headers=headers, timeout=10)
        r.raise_for_status()
        have = {c["name"] for c in r.json()["result"]["collections"]}
        add("PASS", "Live", "Qdrant reachable", f"{url} - {len(have)} collections")
        for col in ["pbd-taxonomy-QA", "pbd-ground-truth-QA"]:
            if col in have:
                cnt = requests.get(f"{url.rstrip('/')}/collections/{col}", headers=headers, timeout=10).json()["result"]["points_count"]
                want = EXPECTED_TAXONOMY_NODES if "taxonomy" in col else EXPECTED_KB_ISSUES
                add("PASS" if cnt == want else "WARN", "Live", f"Collection {col}", f"{cnt} points (expected {want})")
            else:
                add("WARN", "Live", f"Collection {col}", "not found - run the build_*_index.py scripts")
    except ImportError:
        add("SKIP", "Live", "Qdrant reachable", "requests not installed")
    except Exception as exc:
        add("WARN", "Live", "Qdrant reachable", f"{url} not reachable ({type(exc).__name__}) - is Docker running?")


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
ICON = {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL", "SKIP": "⏭️ SKIP"}


def write_report(live: bool):
    counts = {s: sum(1 for r in results if r[0] == s) for s in ICON}
    verdict = ("❌ NOT READY - fix the FAIL items" if counts["FAIL"]
               else "⚠️ READY WITH OPEN ITEMS - see the WARN rows" if counts["WARN"]
               else "✅ READY TO SUBMIT")
    lines = [
        "# Project check report",
        "",
        f"_Generated by `tools/check_project.py{' --live' if live else ''}` on {dt.datetime.now():%Y-%m-%d %H:%M}._  ",
        "_Re-run the script to refresh this file - do not edit it by hand._",
        "",
        f"**Result: {verdict}**",
        "",
        f"| ✅ PASS | ⚠️ WARN | ❌ FAIL | ⏭️ SKIP |",
        f"|---:|---:|---:|---:|",
        f"| {counts['PASS']} | {counts['WARN']} | {counts['FAIL']} | {counts['SKIP']} |",
        "",
    ]
    areas = []
    for r in results:
        if r[1] not in areas:
            areas.append(r[1])
    for area in areas:
        lines += [f"## {area}", "", "| Status | Check | Detail |", "|---|---|---|"]
        for st, ar, chk, det in results:
            if ar == area:
                lines.append(f"| {ICON[st]} | {chk} | {det.replace('|', '/')} |")
        lines.append("")

    todo = [r for r in results if r[0] in ("FAIL", "WARN")]
    lines += ["## What to do next", ""]
    if todo:
        for st, ar, chk, det in todo:
            lines.append(f"- [ ] **{chk}** ({ar}) - {det}")
    else:
        lines.append("Nothing - all checks passed.")
    lines += [""]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    return counts, verdict


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--live", action="store_true", help="also check .env keys and a running Qdrant")
    args = ap.parse_args()

    check_structure(); check_secrets(); check_public_release(); check_python(); check_data()
    check_docs(); check_open_items(); check_hygiene()
    if args.live:
        check_live()

    counts, verdict = write_report(args.live)
    width = max(len(r[2]) for r in results)
    for st, ar, chk, det in results:
        print(f"{ICON[st]:<9} {ar:<9} {chk:<{width}}  {det[:110]}")
    print(f"\n{verdict}\nPASS {counts['PASS']}  WARN {counts['WARN']}  FAIL {counts['FAIL']}  SKIP {counts['SKIP']}")
    print(f"Report written to {REPORT.relative_to(ROOT)}")
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
