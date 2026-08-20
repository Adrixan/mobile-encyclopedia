"""Unit and security acceptance tests for US1.1: Configuration & Vault Storage."""

import os
import stat
from pathlib import Path
import pytest

from offline_vault.config import (
    VaultConfig,
    load_config,
    save_config,
    get_disk_space,
    validate_and_resolve_vault_path,
    ensure_vault_structure,
)


def test_us1_1_default_config(tmp_path):
    config = VaultConfig()
    assert config.locale == "en"
    assert config.vault_dir is not None


def test_us1_1_load_and_save_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    cfg = VaultConfig(
        vault_dir=str(tmp_path / "my_vault"),
        locale="es",
        max_concurrent_downloads=3,
    )
    save_config(cfg, config_path=config_file)
    assert config_file.exists()

    loaded = load_config(config_path=config_file)
    assert loaded.vault_dir == str(tmp_path / "my_vault")
    assert loaded.locale == "es"
    assert loaded.max_concurrent_downloads == 3


def test_us1_1_config_file_permissions_security(tmp_path):
    """Mandatory Security: Ensure config file has restricted permissions (0600)."""
    config_file = tmp_path / "sub" / "config.yaml"
    cfg = VaultConfig(vault_dir=str(tmp_path / "my_vault"))
    save_config(cfg, config_path=config_file)

    # Check file mode
    mode = stat.S_IMODE(os.stat(config_file).st_mode)
    assert mode == 0o600


def test_us1_1_disk_space_calculation(tmp_path):
    total, used, free = get_disk_space(tmp_path)
    assert total > 0
    assert free > 0
    assert total >= free


def test_us1_1_validate_vault_path_success(tmp_path):
    target = tmp_path / "valid_vault"
    resolved = validate_and_resolve_vault_path(str(target), create_if_missing=True)
    assert resolved.exists()
    assert resolved.is_dir()


def test_us1_1_path_traversal_sanitization_security(tmp_path):
    """Mandatory Security: Reject null bytes and unsafe inputs."""
    with pytest.raises(ValueError, match="Invalid or malicious path"):
        validate_and_resolve_vault_path("/tmp/vault\x00/evil")


def test_us1_1_ensure_vault_structure(tmp_path):
    vault = tmp_path / "offline_vault"
    vault.mkdir()
    dirs = ensure_vault_structure(vault)
    for sub in ["admin", "dev", "tutorials", "wiki", "survival", "maps", "qna", "fun", "tools", ".tmp", "logs"]:
        assert (vault / sub).is_dir()
        assert sub in dirs

