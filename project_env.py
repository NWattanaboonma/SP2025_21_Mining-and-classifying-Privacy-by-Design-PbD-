"""
Central place for reading secrets (API keys, tokens).

Every script that needs a key gets it through `get_secret()` - no script reads
keys any other way, and no key is ever written in source code.

Where the keys come from (first match wins):
  1. variables already set in the environment (e.g. `set OPENAI_API_KEY=...`)
  2. the file named by the ENV_FILE environment variable, if set
     -> use this to keep your keys OUTSIDE the project / OneDrive folder, e.g.
        set ENV_FILE=C:\\Users\\<you>\\secrets\\sp2025.env
  3. `.env` in the project root (git-ignored and excluded from the submission zip)

Never print a secret. Use `mask()` if you must show which key is loaded.
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
_loaded = False


def load_env() -> None:
    """Load ENV_FILE or ROOT/.env once. Existing environment variables are never overwritten."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    candidates = []
    if os.getenv("ENV_FILE"):
        candidates.append(Path(os.environ["ENV_FILE"]).expanduser())
    candidates.append(ROOT_DIR / ".env")
    for path in candidates:
        if path.is_file():
            try:
                from dotenv import load_dotenv
            except ImportError:
                _load_simple(path)
            else:
                load_dotenv(path, override=False)
            return


def _load_simple(path: Path) -> None:
    """Minimal .env parser used only if python-dotenv is not installed."""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _is_placeholder(value: str) -> bool:
    """Values copied from .env.example such as <your-openai-api-key> mean 'not set'."""
    v = value.strip().lower()
    return (v.startswith("<") and v.endswith(">")) or v.startswith("your-") or "xxxx" in v


def get_secret(name: str, required: bool = True):
    """Return the value of `name`, or exit with a clear message if it is required but missing."""
    load_env()
    value = (os.getenv(name) or "").strip().strip('"').strip("'")
    if value and _is_placeholder(value):
        value = ""
    if not value:
        if required:
            raise SystemExit(
                f"Missing {name}. Put it in the .env file in the project root "
                f"(see .env.example) - never in the code."
            )
        return None
    return value


def get_setting(name: str, default=None):
    """Non-secret setting (e.g. QDRANT_URL) from the same sources."""
    load_env()
    value = (os.getenv(name) or "").strip()
    if value and _is_placeholder(value):
        value = ""
    return value or default


def mask(value) -> str:
    """Safe display form of a secret: first 4 and last 4 characters only."""
    if not value:
        return "<not set>"
    value = str(value)
    return f"{value[:4]}...{value[-4:]} (length {len(value)})" if len(value) > 12 else "****"
