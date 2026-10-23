# Session Handoff (2026-10-23, Sprint 6)

## Trajectory
- Morning: full review (findings below were the input). Then Peter decided: Kolibri to ZIMs where available, Kapeli only if it works on Termux/Android (it does not, except Zeal under Termux:X11), tools prebuilt only, everything usable on Android.
- Delivered Epic 8 on branch `feat/android-catalog-v2` (US8.1 to US8.4, see `.agents/plan.md`).

## What changed
- `catalog.py`: typed sources (`kiwix`, `github`, `kolibri`, `url`), `entrypoint`, `extract_subdir`, `serve_root`; formats `docset`/`html` removed.
- `resolver.py` (new): Kiwix library by book name + flavour (24 h disk cache, stale cache offline), `.sha256` sidecars, GitHub latest release asset + digest, HTTPS-only results.
- `downloader.py`: no URL guessing; file signature checks; truncation detection; HTTP 416 restart; aria2 runs in a private work dir (Kiwix metalinks rename the output, which previously left full duplicate files in `.tmp/` and forced a second download); partial discarded before the Python fallback.
- `sync.py` (rewritten): manifest `<vault>/.offline-vault/manifest.json`, skip when current, update when upstream URL changed, SHA-256 check, safe extraction (regular files only, no traversal/links, size guard), staging + swap with rollback, redirect `index.html` to entrypoint, per-item error isolation. Fuzzy pruning removed.
- `kolibri.py` (new): `KOLIBRI_CONTENT_DIR=<vault>/tutorials/kolibri/KOLIBRI_DATA/content`, `KOLIBRI_HOME` in `~/.local/share/offline-vault/kolibri-home`.
- `server.py`: library.xml rebuilt from scratch, manifest-based portal links, host-relative server links, HTML escaping, `serve_root` apps on port+1.. with SPA fallback.
- `cli.py`: `status --vault-dir` honoured without creating dirs, combined `--category`/`--language`, lazy TUI import. `tui.py`: cursor kept on toggle, `/` and Esc bindings, no forced re-download, thread-safe finish, error list.
- Catalog: 69 items generated from live data with `.scratch/gen_catalog.py` + `.scratch/catalog_spec.yaml` (local only, git-excluded).

## Verification
- 91 tests green; `pip-audit` clean after upgrading urllib3 2.8.0 / certifi 2026.10.19 in the venv.
- Live sync of 11 items incl. aria2 + Kiwix metalink; manifest shows SHA-256 for Kiwix and GitHub items; second run skips all.
- Browser (Playwright) via `offline-vault serve`: CyberChef, IT-Tools (port 8766 in test), draw.io, CircuitJS1, SQLime (query executed), GeoGebra (command evaluated), OWASP site. Only cosmetic external requests remain (favicons, fonts, Dropbox button).
- Kolibri 0.19.5: `importchannel` + `importcontent --node_ids` wrote the export layout into the vault, no device provisioning needed.

## Open decisions / next steps
- Not tested on a real Android device: Kiwix Play build file picker, Kolibri app folder import under scoped storage, Termux `pip install kolibri`.
- Backlog in `.agents/to-do.md`: server default bind 0.0.0.0 and directory listing, lockfile + audit gate, unused i18n, portal branding, project AGENTS.md, catalog generator into `scripts/`.
