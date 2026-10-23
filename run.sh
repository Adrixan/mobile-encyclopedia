#!/usr/bin/env bash
# ==============================================================================
# Offline Vault Bootstrap & Launcher Script
# Works seamlessly across Linux PCs and Android (Termux)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
VENV_BIN="${VENV_DIR}/bin"

# 1. Detect Python 3 (3.10 or newer)
PYTHON_EXEC=""
for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1 && "${candidate}" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        PYTHON_EXEC="${candidate}"
        break
    fi
done
if [ -z "${PYTHON_EXEC}" ]; then
    echo -e "\e[31m[ERROR]\e[0m Python 3.10+ is not installed. Please install it (e.g., 'pkg install python' or 'sudo zypper install python3')."
    exit 1
fi

# 2. Create the virtual environment and install pinned, hash-verified dependencies.
#    Reinstalls whenever the lockfiles change, so existing installs pick up dependency updates.
LOCK_STAMP="${VENV_DIR}/.offline-vault-locks.sha256"
LOCK_SUM="$(cat "${SCRIPT_DIR}/requirements-build.lock" "${SCRIPT_DIR}/requirements.lock" | sha256sum | cut -d' ' -f1)"
if [ ! -f "${VENV_BIN}/offline-vault" ] || [ ! -f "${LOCK_STAMP}" ] || [ "$(cat "${LOCK_STAMP}")" != "${LOCK_SUM}" ]; then
    echo -e "\e[34m[INFO]\e[0m Setting up Python virtual environment in ${VENV_DIR}..."
    if [ ! -d "${VENV_DIR}" ]; then
        "${PYTHON_EXEC}" -m venv "${VENV_DIR}"
    fi

    echo -e "\e[34m[INFO]\e[0m Installing pinned dependencies (hash-verified)..."
    "${VENV_BIN}/pip" install --disable-pip-version-check --require-hashes \
        -r "${SCRIPT_DIR}/requirements-build.lock" -r "${SCRIPT_DIR}/requirements.lock"
    # The app itself: no dependency resolution and no build isolation, so nothing unpinned is fetched
    "${VENV_BIN}/pip" install --disable-pip-version-check --no-deps --no-build-isolation -e "${SCRIPT_DIR}"
    echo "${LOCK_SUM}" > "${LOCK_STAMP}"
    echo -e "\e[32m[SUCCESS]\e[0m Environment ready!"
fi

# 3. Launch Offline Vault with all passed arguments
exec "${VENV_BIN}/offline-vault" "$@"
