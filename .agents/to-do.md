# Sprint Backlog & To-Do

## Sprint 6 (Epic 8: Android-First Catalog v2 & Safe Sync)
- [x] US8.1 Safe Sync Engine (5 pts) — PASS
- [x] US8.2 Catalog v2 with Typed Sources (5 pts) — PASS
- [x] US8.3 Kolibri Channel Import (3 pts) — PASS
- [x] US8.4 Android Access Paths (3 pts) — PASS

## Quality Gates (Sprint 6)
- [x] 91 tests green (`pytest`), including regression tests for every review finding fixed.
- [x] Live end-to-end sync of 11 items (aria2c path, Kiwix metalink, SHA-256 from Kiwix and GitHub).
- [x] All 6 tools plus the OWASP site verified in a browser via `offline-vault serve`.
- [x] Kolibri import verified with Kolibri 0.19.5 (`importchannel`/`importcontent` into the vault layout).
- [x] `pip-audit`: no known vulnerabilities in the venv.

## Sprint 7 (Epic 9: Tool Replacements, Personal Material, Starter Set)
- [x] US9.1 Replacements for removed tools (3 pts) — PASS
- [x] US9.2 Android apps in the vault (3 pts) — PASS
- [x] US9.3 Personal offline material (3 pts) — PASS
- [x] US9.4 Phone starter set (2 pts) — PASS
- [x] 102 tests green; live sync of 19 new items incl. OpenAndroMaps (1.2 GB); offline browser check of Excalidraw, Drawnix, periodic table, sun/moon demos, IT-Tools.

## Sprint 8 (Epic 10: Privacy Patches, English Defaults, Localhost-Only Serving)
- [x] US10.1 Catalog-defined patches (3 pts) — PASS
- [x] US10.2 Localhost-only servers (2 pts) — PASS
- [x] 110 tests green; live reinstall of the three patched apps; browser with internet allowed: zero outside requests at startup for Excalidraw, Drawnix, periodic table; English UI; `ss` shows 127.0.0.1 for portal, root-app ports and a real Kolibri 0.19.5; LAN address refused.
- [x] Found and fixed: `serve --kolibri` failed on a fresh device (KOLIBRI_HOME parent missing).

## Chore (2026-10-23)
- [x] Catalog generator tracked in git: `scripts/generate_catalog.py` + `scripts/catalog_spec.yaml` (spec is the source of truth); indexes cached in `.scratch/catalog-inputs/`; `tests/test_catalog_generator.py` (offline generator tests + spec/catalog drift check); `.scratch/` in `.gitignore`.

## Sprint 9 (Epic 11: Self-Contained Updates & Backlog Closure)
- [x] US11.1 Self-contained catalog refresh (5 pts) — PASS
- [x] US11.2 Updates for fixed URLs, `index` source (3 pts) — PASS
- [x] US11.3 Server hardening (1 pt) — PASS
- [x] US11.4 Lockfiles and audit gate (3 pts) — PASS
- [x] US11.5 i18n with German (3 pts) — PASS
- [x] US11.6 Concurrent downloads (2 pts) — PASS
- [x] US11.7 Portal branding (1 pt) — PASS
- [x] US11.8 Project AGENTS.md (1 pt) — PASS
- [x] 137 tests green; `scripts/check.sh` green (locks consistent, pip-audit clean); actionlint clean; fresh `run.sh` bootstrap from hashed locks; live user-style `offline-vault refresh` without token (131/134 refreshed, 3 kept packaged values on 429/timeout); live concurrent sync; portal screenshot.
- [x] Found and fixed on the way: fixed-URL items never updated after first sync; eager `setdefault` made pinned sizes hit the network; resume marker ignored version changes; locale path traversal.

## Backlog
- Not tested on a device: APK installs from the vault, Kiwix APK scanning the vault folder, Kolibri app folder import, Termux `pip install kolibri`.
- Help screen text and footer key labels are English only.
- Standard Ebooks rate-limits per IP (bare 429, no Retry-After); syncing many titles at once may need a second run.

## Decisions (kept as is)
- LAN/hotspot sharing removed on request (2026-10-23); re-adding needs an explicit opt-in flag.
- Periodic table element photos load from third-party hosts when online (not tracking).

## Completed Sprints 1-5
- [x] US1.1, US2.1, US3.1, US4.1, US5.1, US6.1, US6.2, US6.3, US6.4, US7.1 (52 pts)
