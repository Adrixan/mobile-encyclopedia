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
    assert "openSUSE" in captured.out or "opensuse" in captured.out.lower()
    assert "Wikipedia" in captured.out or "wikipedia" in captured.out.lower()


def test_us5_1_cli_list_filter_category(capsys):
    ret = run_cli(["list", "--category", "admin"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "openSUSE" in captured.out or "ArchWiki" in captured.out


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
