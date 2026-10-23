"""Kolibri channel import into an export-compatible vault layout.

Content lands in ``<vault>/tutorials/kolibri/KOLIBRI_DATA/content``: the same layout
``kolibri manage exportchannel`` produces, so the vault folder works as a Kolibri
"local drive" for other devices, while the local server reads it in place.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Tuple

KOLIBRI_EXPORT_FOLDER = "KOLIBRI_DATA"
IMPORT_TIMEOUT_SEC = 24 * 3600

INSTALL_HINT = (
    "Kolibri is not installed. Install it with 'pip install kolibri' "
    "(Linux or Termux: pkg install python && pip install kolibri)."
)


def kolibri_root(vault_dir: Path) -> Path:
    """Folder inside the vault that holds Kolibri content (select it as 'drive' in Kolibri)."""
    return Path(vault_dir) / "tutorials" / "kolibri"


def kolibri_content_dir(vault_dir: Path) -> Path:
    """Kolibri content directory (databases/ and storage/) inside the vault."""
    return kolibri_root(vault_dir) / KOLIBRI_EXPORT_FOLDER / "content"


def kolibri_home_dir() -> Path:
    """KOLIBRI_HOME in local app storage: SQLite is unreliable on Android shared storage."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "offline-vault" / "kolibri-home"


def channel_database_path(vault_dir: Path, channel_id: str) -> Path:
    """Path of a channel's metadata database once imported."""
    return kolibri_content_dir(vault_dir) / "databases" / f"{channel_id}.sqlite3"


def kolibri_env(vault_dir: Path, base_env: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Environment for Kolibri commands sharing one content dir between import and serve."""
    env = dict(os.environ if base_env is None else base_env)
    env["KOLIBRI_HOME"] = str(kolibri_home_dir())
    env["KOLIBRI_CONTENT_DIR"] = str(kolibri_content_dir(vault_dir))
    return env


def find_kolibri_executable() -> Optional[str]:
    """Locate Kolibri executable in active virtualenv or system PATH."""
    venv_kolibri = Path(sys.executable).parent / "kolibri"
    if venv_kolibri.is_file() and os.access(venv_kolibri, os.X_OK):
        return str(venv_kolibri)
    return shutil.which("kolibri")


def _tail(text: str, lines: int = 5) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def import_channel(
    vault_dir: Path,
    channel_id: str,
    executable: Optional[str] = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> Tuple[bool, str]:
    """Import channel metadata and all its content from Kolibri Studio into the vault."""
    kolibri_bin = executable or find_kolibri_executable()
    if not kolibri_bin:
        return False, INSTALL_HINT

    vault_dir = Path(vault_dir)
    kolibri_content_dir(vault_dir).mkdir(parents=True, exist_ok=True)
    kolibri_home_dir().mkdir(parents=True, exist_ok=True)
    env = kolibri_env(vault_dir)

    for step in ("importchannel", "importcontent"):
        cmd = [kolibri_bin, "manage", step, "network", channel_id]
        try:
            proc = runner(cmd, env=env, capture_output=True, text=True, check=False, timeout=IMPORT_TIMEOUT_SEC)
        except (OSError, subprocess.SubprocessError) as e:
            return False, f"kolibri {step} failed: {e}"
        if proc.returncode != 0:
            output = _tail(f"{proc.stdout or ''}\n{proc.stderr or ''}")
            return False, f"kolibri {step} exited with code {proc.returncode}: {output}"

    if not channel_database_path(vault_dir, channel_id).is_file():
        return False, "Kolibri reported success but the channel database is missing"
    return True, "Channel imported"
