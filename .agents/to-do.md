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

## Backlog (from the 2026-10-23 review, not in Sprint 6)
- Excalidraw's Docker build includes an analytics script (loads only when online); stripping it would mean patching upstream files.
- Drawnix and the periodic table default to a Chinese UI.
- Catalog generator (`.scratch/gen_catalog.py` + `catalog_spec.yaml`, local only) could move into `scripts/` so sizes can be refreshed; needs a decision on spec vs. YAML as source of truth.
- CircuitJS1 URL is version-pinned (Falstad has no "latest" link); GitHub branch archives (OWASP, SQLime) carry no checksum.
- Kolibri Android "import from folder" with Android scoped storage not tested on a device.
- Static server binds 0.0.0.0 with directory listing; `--host` ignored for Kiwix and Kolibri.
- Lockfile with exact pins (`uv lock`) and a `pip-audit` gate.
- i18n is wired but unused; `max_concurrent_downloads` unused.
- Portal styling to Bioluminescent Night tokens.
- Project `AGENTS.md` plus `CLAUDE.md` (`@AGENTS.md`).

## Completed Sprints 1-5
- [x] US1.1, US2.1, US3.1, US4.1, US5.1, US6.1, US6.2, US6.3, US6.4, US7.1 (52 pts)
