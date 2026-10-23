"""Isolate every test from the user's real data and cache directories."""

import pytest


@pytest.fixture(autouse=True)
def isolated_user_dirs(tmp_path_factory, monkeypatch):
    base = tmp_path_factory.mktemp("xdg")
    monkeypatch.setenv("XDG_DATA_HOME", str(base / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(base / "cache"))
