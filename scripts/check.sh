#!/usr/bin/env bash
# Quality gate before committing (CI runs the same steps): tests, lockfile consistency, dependency audit.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PIP_AUDIT_VERSION="2.10.1"

echo "== tests"
.venv/bin/python -m pytest -q

echo "== lockfiles match pyproject.toml"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
COMPILE=(uv pip compile --universal --python-version 3.10 --generate-hashes --no-header -q)
cp requirements.lock requirements-dev.lock "${tmp}/"
"${COMPILE[@]}" pyproject.toml -o "${tmp}/requirements.lock"
"${COMPILE[@]}" pyproject.toml --extra dev -o "${tmp}/requirements-dev.lock"
diff -u requirements.lock "${tmp}/requirements.lock"
diff -u requirements-dev.lock "${tmp}/requirements-dev.lock"

echo "== dependency audit"
uvx "pip-audit==${PIP_AUDIT_VERSION}" --progress-spinner off --disable-pip --require-hashes \
    -r requirements-dev.lock -r requirements-build.lock
echo "All checks passed."
