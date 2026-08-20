"""Configuration and storage vault management for offline-vault."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def is_termux() -> bool:
    """Detect if running inside an Android Termux environment."""
    return "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")


def get_default_vault_dir() -> Path:
    """Return default vault directory based on environment."""
    if is_termux():
        # Android shared download storage if accessible, else home directory
        sdcard_download = Path("/sdcard/Download/offline_vault")
        if sdcard_download.parent.exists() and os.access(sdcard_download.parent, os.W_OK):
            return sdcard_download
        return Path.home() / "offline_vault"
    return Path.home() / "offline_vault"


def get_default_config_dir() -> Path:
    """Return default config directory (~/.config/offline-vault)."""
    return Path.home() / ".config" / "offline-vault"


def get_default_config_path() -> Path:
    """Return default config file path (~/.config/offline-vault/config.yaml)."""
    return get_default_config_dir() / "config.yaml"


@dataclass
class VaultConfig:
    """Configuration settings for Offline Vault."""

    vault_dir: str = ""
    locale: str = "en"
    max_concurrent_downloads: int = 2
    prefer_aria2: bool = True
    aria2_split_connections: int = 4
    enable_kiwix_indexing: bool = True

    def __post_init__(self) -> None:
        if not self.vault_dir:
            self.vault_dir = str(get_default_vault_dir())


def load_config(config_path: Optional[Path] = None) -> VaultConfig:
    """Load configuration from YAML file or return defaults."""
    path = config_path or get_default_config_path()
    if not path.is_file():
        return VaultConfig()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return VaultConfig()
        return VaultConfig(**{k: v for k, v in data.items() if k in VaultConfig.__dataclass_fields__})
    except Exception:
        return VaultConfig()


def save_config(config: VaultConfig, config_path: Optional[Path] = None) -> Path:
    """Save configuration to YAML file with secure permissions (0600/0700)."""
    path = config_path or get_default_config_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    data = asdict(config)
    # Write atomically
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False)

    # Set secure permissions (0600)
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)
    os.chmod(path, 0o600)
    return path


def get_disk_space(target_path: Path | str) -> Tuple[int, int, int]:
    """Return (total_bytes, used_bytes, free_bytes) for the given path mount."""
    path = Path(target_path).resolve()
    # Find existing ancestor if path doesn't exist yet
    while not path.exists() and path.parent != path:
        path = path.parent
    usage = shutil.disk_usage(path)
    return usage.total, usage.used, usage.free


def validate_and_resolve_vault_path(raw_path: str, create_if_missing: bool = True) -> Path:
    """Sanitize, normalize, and resolve vault path. Prevent null bytes and invalid characters."""
    if not raw_path or "\x00" in raw_path:
        raise ValueError("Invalid or malicious path specified")

    resolved = Path(raw_path).expanduser().resolve()

    if create_if_missing:
        resolved.mkdir(parents=True, exist_ok=True)

    return resolved


def ensure_vault_structure(vault_root: Path) -> Dict[str, Path]:
    """Ensure vault subdirectories exist matching TUI categories."""
    subdirs = ["admin", "dev", "tutorials", "wiki", "survival", "maps", "qna", "fun", ".tmp", "logs"]
    created: Dict[str, Path] = {}
    for sub in subdirs:
        sub_path = vault_root / sub
        sub_path.mkdir(parents=True, exist_ok=True)
        created[sub] = sub_path
    return created

