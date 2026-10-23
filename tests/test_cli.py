"""Tests for the CLI interface and commands."""

from pathlib import Path
import pytest

from offline_vault.cli import build_parser, run_cli
from offline_vault.config import VaultConfig


def test_us5_1_cli_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None or args.command == "tui"


def test_us5_1_cli_list_command(capsys):
    ret = run_cli(["list"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ArchWiki" in captured.out
    assert "Wikipedia" in captured.out or "wikipedia" in captured.out.lower()


def test_us5_1_cli_list_filter_category(capsys):
    ret = run_cli(["list", "--category", "admin"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ArchWiki" in captured.out


def test_us5_1_cli_list_filter_language(capsys):
    ret = run_cli(["list", "--language", "bs"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Bosnian" in captured.out or "bs" in captured.out


def test_us5_1_cli_status_command(tmp_path, capsys):
    ret = run_cli(["status", "--vault-dir", str(tmp_path)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Vault Directory" in captured.out
    assert "Available Disk Space" in captured.out


def test_cli_serve_subcommand_routes_to_static_server(tmp_path):
    from unittest.mock import patch
    with patch("offline_vault.server.run_static_server", return_value=0) as mock_static:
        ret = run_cli(["serve", "--static", "--port", "9090", "--vault-dir", str(tmp_path)])
        assert ret == 0
        mock_static.assert_called_once()
        _, kwargs = mock_static.call_args
        assert kwargs["port"] == 9090
        assert kwargs["vault_dir"] == tmp_path.resolve()


def test_status_honours_vault_dir_override_without_creating_dirs(tmp_path, monkeypatch, capsys):
    from offline_vault import cli

    configured = tmp_path / "configured"
    override = tmp_path / "override"
    override.mkdir()
    (override / "wiki").mkdir()
    (override / "wiki" / "wikipedia_en_top.zim").write_bytes(b"ZIM\x04data")
    monkeypatch.setattr(cli, "load_config", lambda: VaultConfig(vault_dir=str(configured)))

    assert run_cli(["status", "--vault-dir", str(override)]) == 0
    out = capsys.readouterr().out
    assert str(override) in out
    assert "Downloaded Resources: 1" in out
    assert not configured.exists()
    assert not (override / "admin").exists()


def test_sync_combines_category_and_language_filters(tmp_path, monkeypatch):
    from offline_vault import cli

    captured = {}

    def fake_sync(self, item_ids, force_update=False, **kwargs):
        captured["ids"] = set(item_ids)
        from offline_vault.sync import SyncSummary
        return SyncSummary(len(captured["ids"]), 0, 0, len(captured["ids"]), 0, {})

    monkeypatch.setattr("offline_vault.sync.SyncManager.sync_items", fake_sync)
    assert run_cli(["sync", "--category", "wiki", "--language", "bs", "--vault-dir", str(tmp_path)]) == 0
    from offline_vault.catalog import load_catalog
    catalog = load_catalog()
    expected = {i.id for i in catalog.items if i.category == "wiki" and i.language == "bs"}
    assert expected and captured["ids"] == expected
