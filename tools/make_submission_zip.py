"""
Build the zip file to hand in - with NO secrets inside.

What it does:
  1. collects every project file EXCEPT secrets and local junk
     (.env, *.pem, *.key, App.env, .venv/, __pycache__/, qdrant_storage/, n8n_data/, data/raw/, dist/ ...)
  2. scans every text file it is about to add for API-key patterns
  3. if anything looks like a key -> STOPS and creates no zip
  4. otherwise writes dist/<folder-name>_submission_<date>.zip

Usage (from the project root):

    python tools/make_submission_zip.py
    python tools/make_submission_zip.py --list      # only show what would be included
"""

import argparse
import datetime as dt
import fnmatch
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", "qdrant_storage",
                "n8n_data", "dist", ".idea", ".vscode", ".pytest_cache", "_n8n_export_all", "_private"}
EXCLUDE_PATHS = ["data/raw/*", "data/issues/*", "docs/CHECK_REPORT.md", "06_evaluation/earlier_experiment/*"]
EXCLUDE_FILES = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "App.env", "id_rsa*",
                 "*.zip", ".DS_Store", "Thumbs.db", "*.pyc", "~$*"]
KEEP_FILES = [".env.example"]          # template without values - safe and useful

SECRET_PATTERNS = {
    "OpenAI key": r"sk-(proj-)?[A-Za-z0-9_-]{20,}",
    "Anthropic key": r"sk-ant-[A-Za-z0-9_-]{20,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{30,}",
    "GitHub token": r"(ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}",
    "JWT / Qdrant key": r"eyJhbGciOi[A-Za-z0-9_.-]{20,}",
    "Private key": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Key assigned in code": r"""(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*["'][A-Za-z0-9_\-]{24,}["']""",
}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".csv", ".toml", ".cfg", ".ini",
                 ".sh", ".bat", ".ps1", ".js", ".ts", ".html", ".example", ""}
SELF = {"make_submission_zip.py", "check_project.py"}   # these files contain the patterns on purpose

# Personal identifiers of the authors' machines. Checked only in code / docs / workflows and in Office
# *metadata* - NOT in research data, because public GitHub issue texts legitimately contain paths.
PERSONAL_PATTERNS = {
    "Personal Windows path": r"[A-Za-z]:\\{1,2}Users\\{1,2}(?!<|YOUR_)[A-Za-z0-9._-]+\\{1,2}",
    "OneDrive account path": r"d\.docs\.live\.net/[0-9a-f]{8,}",
}
CODE_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".example", ".toml", ".cfg", ".ini", ".sh", ".bat", ".ps1"}
OFFICE_SUFFIXES = {".xlsx", ".xlsm", ".docx", ".pptx"}


def is_code_or_doc(rel: Path) -> bool:
    return rel.suffix.lower() in CODE_SUFFIXES or (rel.suffix.lower() == ".json" and "n8n" in rel.parts)


def office_metadata(path: Path) -> bytes:
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n in ("xl/workbook.xml", "word/settings.xml") or n.startswith("docProps/")]
            return b"".join(z.read(n) for n in names)
    except zipfile.BadZipFile:
        return b""


def excluded(rel: Path) -> bool:
    if set(rel.parts[:-1]) & EXCLUDE_DIRS or rel.parts[0] in EXCLUDE_DIRS:
        return True
    posix = rel.as_posix()
    if any(fnmatch.fnmatch(posix, p) for p in EXCLUDE_PATHS):
        return True
    if rel.name in KEEP_FILES:
        return False
    return any(fnmatch.fnmatch(rel.name, p) for p in EXCLUDE_FILES)


def scan(path: Path):
    if path.name in SELF:
        return []
    rel = path.relative_to(ROOT)
    if path.suffix.lower() in OFFICE_SUFFIXES:
        meta = office_metadata(path)
        hits = []
        if b"absPath" in meta or b"docs.live.net" in meta:
            hits.append("hidden folder path in Office metadata")
        if re.search(rb"[A-Za-z]:\\{1,2}Users\\{1,2}(?!<|YOUR_)[A-Za-z0-9._-]+", meta):
            hits.append("personal Windows path in Office metadata")
        return hits
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits = [name for name, pat in SECRET_PATTERNS.items() if re.search(pat, text)]
    if is_code_or_doc(rel):
        hits += [name for name, pat in PERSONAL_PATTERNS.items() if re.search(pat, text)]
    return hits


def check_env_example():
    """The template must not contain real values."""
    ex = ROOT / ".env.example"
    bad = []
    if ex.exists():
        for line in ex.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                value = value.strip()
                if value and not value.startswith("http") and not value.startswith("<"):
                    bad.append(key.strip())
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--list", action="store_true", help="only list the files that would be included")
    args = ap.parse_args()

    files, skipped, problems = [], [], []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if excluded(rel):
            skipped.append(rel)
            continue
        hits = scan(p)
        if hits:
            problems.append(f"{rel}: {', '.join(hits)}")
        files.append(rel)

    for key in check_env_example():
        problems.append(f".env.example: {key} has a value - the template must stay empty")

    secret_like = [s for s in skipped if s.name in (".env", "App.env") or s.suffix in (".pem", ".key")]
    print(f"Included: {len(files)} files   Excluded: {len(skipped)} files")
    if secret_like:
        print("Secret files left out on purpose:", ", ".join(str(s) for s in secret_like))

    if problems:
        print("\nSTOPPED - possible secrets found. No zip was created. Fix these first:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    if args.list:
        for f in files:
            print("  ", f.as_posix())
        return

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{ROOT.name}_submission_{dt.date.today():%Y%m%d}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(ROOT / rel, Path(ROOT.name) / rel)

    # final double-check on the finished zip
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        leaked = [n for n in names if Path(n).name in (".env", "App.env") or n.endswith((".pem", ".key"))]
    if leaked:
        out.unlink()
        sys.exit(f"STOPPED - secret files ended up in the zip ({leaked}); zip deleted.")

    print(f"\nOK - {out.relative_to(ROOT)}  ({out.stat().st_size / 1e6:.1f} MB, {len(names)} files, no secrets found)")


if __name__ == "__main__":
    main()
