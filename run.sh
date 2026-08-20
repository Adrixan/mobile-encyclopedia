#!/usr/bin/env bash
# ==============================================================================
# Offline Vault Bootstrap & Launcher Script
# Works seamlessly across Linux PCs and Android (Termux)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
VENV_BIN="${VENV_DIR}/bin"

# 1. Detect Python 3
if command -v python3 >/dev/null 2>&1; then
    PYTHON_EXEC="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXEC="python"
else
    echo -e "\e[31m[ERROR]\e[0m Python 3 is not installed. Please install Python 3 (e.g., 'pkg install python' or 'sudo zypper install python3')."
    exit 1
fi

# 2. Check and initialize virtual environment if missing
if [ ! -f "${VENV_BIN}/offline-vault" ]; then
    echo -e "\e[34m[INFO]\e[0m Setting up Python virtual environment in ${VENV_DIR}..."
    if [ ! -d "${VENV_DIR}" ]; then
        "${PYTHON_EXEC}" -m venv "${VENV_DIR}"
    fi

    echo -e "\e[34m[INFO]\e[0m Installing Offline Vault and dependencies..."
    "${VENV_BIN}/pip" install --upgrade pip >/dev/null 2>&1 || true
    "${VENV_BIN}/pip" install -e "${SCRIPT_DIR}"
    echo -e "\e[32m[SUCCESS]\e[0m Environment ready!"
fi

# 3. Launch Offline Vault with all passed arguments
exec "${VENV_BIN}/offline-vault" "$@"
