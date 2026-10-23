"""Maintainer tool: regenerate the packaged catalog from the packaged spec (strict mode).

Fails on any entry that cannot be resolved, so a broken source never ships. End users refresh their
own catalog with `offline-vault refresh` instead (tolerant, no token needed).

    GITHUB_TOKEN=$(gh auth token) .venv/bin/python scripts/generate_catalog.py [--refresh]
"""

import sys
from pathlib import Path

from offline_vault.catalog_builder import main

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    sys.exit(main(["--cache-dir", str(ROOT / ".scratch" / "catalog-inputs"), *sys.argv[1:]]))
