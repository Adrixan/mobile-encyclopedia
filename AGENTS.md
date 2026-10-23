# Offline Vault: Agent Instructions

Offline knowledge manager for Linux and Android (Termux): curates, downloads, verifies, updates and serves offline content (Kiwix ZIMs, EPUBs, Mapsforge maps, web apps, Kolibri channels, APKs). Python 3.10+, Textual TUI, Rich CLI.

## Commands
- Run: `./run.sh [command]` (creates `.venv` from the hash-pinned locks; reinstalls when the locks change).
- Tests: `.venv/bin/python -m pytest -q`.
- Quality gate before every commit: `scripts/check.sh` (tests, lock consistency, `pip-audit`). CI (`.github/workflows/ci.yml`) runs the same on Python 3.10 and 3.13, plus weekly.
- Refresh the user catalog (what end users run): `offline-vault refresh [--force]`.
- Regenerate the packaged catalog (maintainers, strict): `GITHUB_TOKEN=$(gh auth token) .venv/bin/python scripts/generate_catalog.py`.
- Upgrade dependencies: `scripts/update-locks.sh`, review the diff, then `scripts/check.sh`.

## Layout
- `src/offline_vault/`: `catalog.py` (schema, validation, catalog selection), `catalog_builder.py` (spec to catalog, tolerant and strict modes), `resolver.py` (latest upstream versions), `downloader.py` (aria2c plus Python fallback, signatures), `sync.py` (manifest, safe extraction, patches, atomic installs, concurrency), `kolibri.py`, `server.py` (localhost-only servers, portal), `cli.py`, `tui.py`, `i18n.py`, `locales/`.
- `src/offline_vault/data/catalog_spec.yaml`: source of truth for catalog contents. `data/catalog.yaml` is generated; never edit it by hand.
- `scripts/`: maintainer tools. `.agents/`: sprint state (`plan.md`, `to-do.md`, `project-state.md`, `session-handoff.md`).

## Rules
- Catalog: every item needs a real, typed upstream source (`kiwix`, `github`, `oci`, `fdroid`, `kolibri`, `index`, `url`) and must be usable on Android (app reading the vault folder, or Termux plus browser). No placeholder or duplicate URLs. Phone-sized by default; items over 20 GB must say "large" in their description.
- Nothing upstream is bundled: tools and content are fetched at sync time. Web apps must be prebuilt; no build steps on the device.
- Patches (`patches:` in the spec) strip trackers and set defaults. They must keep failing loudly when they stop matching; never make a patch optional to get an install through.
- Security: HTTPS only; verify file signatures and SHA-256 where upstream publishes it; archive extraction keeps regular files only (no links, no traversal, size guard); sync never deletes anything outside an item's own path; servers bind to loopback only, without directory listings or dotfiles.
- Downloads must not depend on maintainer credentials; `GITHUB_TOKEN` is optional and only lifts API limits.
- Dependencies: exact, hash-pinned versions in `requirements*.lock`; latest stable releases; no known vulnerabilities (`scripts/check.sh` must pass).
- Translations: every key in `locales/en.json` exists in every locale file (`tests/test_i18n.py` enforces it).
- Workflow: TDD (failing test first, then code); keep `.agents/` state files current; Conventional Commits.
