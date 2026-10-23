#!/usr/bin/env bash
# Regenerate the hash-pinned lockfiles with the latest releases (review the diff, then run scripts/check.sh).
# One universal lock serves Linux and Android/Termux for Python 3.10 and newer.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPILE=(uv pip compile --universal --python-version 3.10 --generate-hashes --no-header --upgrade -q)
"${COMPILE[@]}" pyproject.toml -o requirements.lock
"${COMPILE[@]}" pyproject.toml --extra dev -o requirements-dev.lock
printf 'setuptools>=61.0\n' | "${COMPILE[@]}" - -o requirements-build.lock
git --no-pager diff --stat -- requirements*.lock
