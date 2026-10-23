# Session Handoff (2026-10-23)

## Trajectory
- Full review of the project for bugs, security issues and deviations from `.agents/plan.md`. No source code changed.
- Test suite: 43/43 green, but the tests mock exactly the behaviour that breaks in practice (pruning, extraction, downloads).
- Repro scripts (local only, git-excluded) in `.scratch/`: `check_urls.py`, `check_resolve.py`, `repro_prune.py`, `repro_misc.py`, `repro_tui.py`.

## Verified findings (ranked)
- CRITICAL `sync.py` `prune_old_versions`: keyword match on tags and id tokens deletes other catalog items in the same category. Syncing all 12 wiki items leaves 1 file on disk; syncing `python_docset` deletes all 10 other docsets. TUI always passes `force_update=True`, so every TUI sync re-downloads and prunes.
- CRITICAL catalog: 76 entries share 51 URLs; about 40 entries download something other than their name (placeholder URLs: OWASP/tcpdump/progit/appropedia/explainxkcd reused; all 12 Kolibri entries point to the Studio web page; WHO epub, Kapeli `Python_3`/`PowerShell` return HTML; Debian handbook 404). Sizes off by up to 4x (en nopic 12000 vs 50250 MB).
- CRITICAL security `sync.py` tar extraction: no `filter="data"`; symlink member escapes the vault (reproduced on Python 3.13).
- HIGH: no content-type/size/checksum validation (US3.1 AC4 unmet); HTML error pages stored as success. aria2 to Python fallback resumes a sparse multi-segment partial (corruption, reasoned). Kolibri sync non-functional. Docsets and tarball "epub" never extracted. 5 of 9 tools are source repos or libraries; nested `index.html` symlink breaks relative assets. Static server binds 0.0.0.0 with directory listing; `--host` ignored for Kiwix/Kolibri.
- MEDIUM: TUI cursor jumps to row 0 on every toggle; `/` and Esc bindings missing; widget mutated from worker thread; extraction exception aborts whole sync. `status --vault-dir` ignored. `sync --category` + `--language` not combined. Stale `library.xml` entries. Dashboard links to `localhost` (broken from phones) and port 8000 clash. i18n unused. README F-Droid links for Kiwix, Kolibri, Awh 404; OsmAnd cannot read Mapsforge `.map`.
- DEPS: urllib3 2.7.0 (3 advisories, fixed 2.8.0), certifi 2026.7.22 (fixed 2026.10.19); no lockfile.

## Open decisions (need Peter)
- Fix order and scope: hotfix (prune, tar filter, validation, TUI force flag) first, then catalog rebuild.
- Kolibri: implement `importchannel`/`importcontent` with channel IDs, or replace with Kiwix ZIMs (phet, khanacademy, ted, devdocs).
- Docsets: keep Kapeli (desktop Zeal) or switch to `devdocs_en_*` ZIMs (readable in Kiwix on Android).
- Tools: replace source tarballs with built releases or drop them.

## Next steps
- Add regression tests per finding before fixing (TDD loop), then a manifest (`<vault>/manifest.json`) for update checks and exact pruning.
- Generate Kiwix entries from `library_zim.xml` (name + flavour) with sizes; add a catalog lint test (unique URLs, network check marked).
- `uv lock` with exact pins; add `pip-audit` gate; add project `AGENTS.md` + `CLAUDE.md` (`@AGENTS.md`).
