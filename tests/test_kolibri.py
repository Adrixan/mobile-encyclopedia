"""Tests for US8.3: Kolibri channel import into an export-compatible vault layout."""

import subprocess
from pathlib import Path

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.config import VaultConfig
from offline_vault.kolibri import channel_database_path, import_channel, kolibri_env
from offline_vault.sync import SyncManager

CHANNEL = "3e464ee12f6a50a781cddf59147b48b1"


def test_kolibri_env_points_content_into_vault_and_home_outside(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    env = kolibri_env(tmp_path / "vault", base_env={"PATH": "/usr/bin"})
    assert env["KOLIBRI_CONTENT_DIR"] == str(tmp_path / "vault" / "tutorials" / "kolibri" / "KOLIBRI_DATA" / "content")
    assert env["KOLIBRI_HOME"].startswith(str(tmp_path / "data"))
    assert env["PATH"] == "/usr/bin"


def test_import_channel_runs_network_import_commands(tmp_path):
    calls = []

    def runner(cmd, env=None, **kwargs):
        calls.append((cmd, env))
        if cmd[2] == "importchannel":
            db = channel_database_path(tmp_path, CHANNEL)
            db.parent.mkdir(parents=True, exist_ok=True)
            db.write_bytes(b"SQLite format 3\x00")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    ok, message = import_channel(tmp_path, CHANNEL, executable="/usr/bin/kolibri", runner=runner)
    assert ok, message
    assert [c[0][1:] for c in calls] == [
        ["manage", "importchannel", "network", CHANNEL],
        ["manage", "importcontent", "network", CHANNEL],
    ]
    assert all(c[1]["KOLIBRI_CONTENT_DIR"].endswith("KOLIBRI_DATA/content") for c in calls)


def test_import_channel_reports_failure_output(tmp_path):
    def runner(cmd, env=None, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="line1\nChannel not found")

    ok, message = import_channel(tmp_path, CHANNEL, executable="/usr/bin/kolibri", runner=runner)
    assert not ok
    assert "Channel not found" in message


def test_import_channel_without_kolibri_explains_install(tmp_path, monkeypatch):
    monkeypatch.setattr("offline_vault.kolibri.find_kolibri_executable", lambda: None)
    ok, message = import_channel(tmp_path, CHANNEL)
    assert not ok
    assert "pip install kolibri" in message


def test_sync_routes_kolibri_items_to_importer(tmp_path, monkeypatch):
    item = ResourceItem(id="sikana_en", name="Sikana", category="survival", language="en", format="kolibri",
                        size_mb=1, upstream_url=f"https://studio.learningequality.org/channels/{CHANNEL}",
                        source="kolibri", kolibri_channel=CHANNEL)
    seen = []

    def fake_import(vault, channel, **kwargs):
        seen.append(channel)
        db = channel_database_path(vault, channel)
        db.parent.mkdir(parents=True, exist_ok=True)
        db.write_bytes(b"SQLite format 3\x00")
        return True, "imported"

    monkeypatch.setattr("offline_vault.sync.import_channel", fake_import)
    mgr = SyncManager(VaultConfig(vault_dir=str(tmp_path / "vault")), ResourceCatalog([item]))
    summary = mgr.sync_items([item.id])
    assert summary.completed == 1
    assert seen == [CHANNEL]
    assert mgr.get_destination_for_item(item) == channel_database_path(tmp_path / "vault", CHANNEL)
    assert mgr.sync_items([item.id]).skipped == 1
