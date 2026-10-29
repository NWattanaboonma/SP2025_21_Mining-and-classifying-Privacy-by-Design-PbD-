"""
Check that GITHUB_TOKEN (from .env or the environment) is valid.

Prints only a masked version of the token, never the full value.

Usage:  python tools/check_github_token.py
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_env import get_secret, mask  # noqa: E402

token = get_secret("GITHUB_TOKEN")
print(f"Token loaded: {mask(token)}")
r = requests.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"}, timeout=30)
if r.status_code == 200:
    print(f"OK - authenticated as {r.json()['login']}")
else:
    raise SystemExit(f"ERROR: GitHub returned {r.status_code}: {r.json().get('message')}")
