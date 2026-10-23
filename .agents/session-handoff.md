# Session Handoff (2026-10-23, Sprint 8)

## Trajectory
- Sprints 6 and 7 earlier today: catalog v2 and safe sync, then tool replacements, apps, personal material, starter set (see git history).
- Sprint 8: Peter asked to strip analytics, switch the Chinese-default apps to English, and make the local server listen on localhost only.

## What changed
- `catalog.py`: `patches` field (file glob, regex, replace), validated; `patches_digest` fingerprint.
- `sync.py`: `apply_patches` runs in staging before the atomic swap; every patch must match or the install fails and the old version stays; manifest stores the patch fingerprint, so patch changes trigger a reinstall.
- Catalog: Excalidraw (4 patches: analytics script, CDN asset path, CDN font preloads, CSS CDN font sources), Drawnix (Umami removed, `localStorage.language=en` seeded only if unset, lang/title), periodic table (`currentLanguage:"en"`, lang/title).
- `server.py`/`cli.py`: default host 127.0.0.1; `is_loopback_host` guard in CLI (exit 2) and in every server runner; kiwix-serve gets `--address=127.0.0.1` (its default is all interfaces); Kolibri gets `KOLIBRI_LISTEN_ADDRESS`; LAN URL printing and `get_lan_ip` removed; portal text says localhost only. `serve --kolibri` now creates KOLIBRI_HOME (fresh-device bug).
- README and TUI help: no LAN/hotspot sharing; privacy patches documented.

## Verification
- 110 tests green (red first for every change).
- Live: the three apps reinstalled from upstream with patches applied; browser with internet allowed recorded zero outside requests at startup; Drawnix and the periodic table render in English.
- `ss -ltn`: 127.0.0.1 for portal (8765) and root apps (8766, 8767); real Kolibri 0.19.5 on 127.0.0.1:8090; LAN IP refused; `--host 0.0.0.0` rejected.
- kiwix-serve not installed locally; `--address` verified in kiwix-tools source.

## Exit check (end of session)
- Peter asked whether web tools are bundled: they are not. The wheel is 58 KB (Python modules, `catalog.yaml`, locales); every tool, ZIM, EPUB, map and APK is fetched from upstream at sync time and patched on the device. Patches are text rules in `catalog.yaml`.
- Generator usage is documented in `.scratch/README.md` (local only, git-excluded): refresh `library_zim.xml` and `kolibri_channels.json`, then run `gen_catalog.py` with `GH_TOKEN`.
- State at exit: `main` = `origin/main`, tree clean, no feature branches, 110 tests green. `origin/chore/drop-copilot-kilo` is an older, already merged branch left in place.

## Open decisions / next steps
- Not tested on a device: APK installs from the vault, Kiwix APK scanning the vault folder.
- Backlog: directory listing, lockfile + audit gate, unused i18n, portal branding, project AGENTS.md, generator into `scripts/` (generator and spec live only in `.scratch/`).
