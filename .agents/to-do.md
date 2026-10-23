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

## Backlog (from the 2026-10-23 review, not in Sprint 6)
- Periodic table element photos load from third-party hosts when online (not tracking, left as is).
- CircuitJS1 URL is version-pinned (Falstad has no "latest" link); GitHub branch archives (OWASP, SQLime) carry no checksum.
- Kolibri Android "import from folder" with Android scoped storage not tested on a device.
- Static server still allows directory listing (now localhost only).
- LAN/hotspot sharing was removed on request (2026-10-23); re-adding it would need an explicit opt-in flag.
- Lockfile with exact pins (`uv lock`) and a `pip-audit` gate.
- i18n is wired but unused; `max_concurrent_downloads` unused.
- Portal styling to Bioluminescent Night tokens.
- Project `AGENTS.md` plus `CLAUDE.md` (`@AGENTS.md`).

## Completed Sprints 1-5
- [x] US1.1, US2.1, US3.1, US4.1, US5.1, US6.1, US6.2, US6.3, US6.4, US7.1 (52 pts)
