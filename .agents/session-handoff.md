# Session Handoff (2026-10-23, Sprint 9)

## Trajectory
- Sprints 6 to 8 earlier today: catalog v2 and safe sync; tool replacements, apps, starter set; privacy patches and localhost-only servers; generator tracked in git.
- Sprint 9: Peter asked to make the app self-contained for index updates and to perform all remaining backlog tasks.

## What changed
- Self-contained refresh: `catalog_builder.py` and `data/catalog_spec.yaml` now live in the package; `offline-vault refresh [--force]` and TUI `R` rebuild `~/.local/share/offline-vault/catalog.yaml` (tolerant, no token); `load_catalog()` uses it only while its `spec_digest` matches the shipped spec. `scripts/generate_catalog.py` is a thin strict wrapper for maintainers.
- Fixed URLs now update: `ResolvedSource.version` from ETag/Last-Modified (HEAD first, ranged GET fallback); manifest stores `version`; legacy records adopt it without re-download; resume markers include it. New `index` source (CircuitJS1 newest bundle from Falstad's listing).
- Server: `VaultRequestHandler` (no listings; dotfiles and `logs/` 404).
- Dependencies: `requirements.lock`, `requirements-dev.lock`, `requirements-build.lock` (universal, hashed); `run.sh` uses them with `--require-hashes` and reinstalls on lock change; `scripts/check.sh` (tests, lock consistency, pip-audit 2.10.1); `scripts/update-locks.sh`; CI workflow (3.10, 3.13, weekly audit; checkout v7.0.1 and setup-uv v10.3.2 pinned by SHA).
- i18n: TUI via `t()`, locales en/de/es/bs with 63 keys, locale names validated (traversal fix). Concurrency: thread pool sized by `max_concurrent_downloads`, locked manifest and Kiwix index, Kolibri sequential; Python downloader retries 429/503 (bounded, Retry-After). Portal: Bioluminescent Night. `AGENTS.md` + `CLAUDE.md` added (public repo: project rules only).

## Bugs found and fixed
- Fixed-URL items (Mapsforge, GeoGebra, branch archives, OpenAndroMaps, EPUBs) were never updated after the first sync.
- `entry.setdefault("size_mb", url_size(...))` evaluated eagerly: pinned sizes still hit the network (rate limits on Standard Ebooks).
- Resume of a partial from an older version of the same URL; locale path traversal.

## Verification
- 137 tests; `scripts/check.sh` green; actionlint clean; fresh `run.sh` bootstrap from locks in a copy of the repo.
- Live `offline-vault refresh` without token in isolated dirs: 131/134 refreshed, 3 kept packaged values (Standard Ebooks 429, GeoGebra timeout).
- Live concurrent sync (3 workers) of 6 items, second run skipped all; IF game Last-Modified recorded; portal screenshot and 404 checks.
- Standard Ebooks currently answers 429 to this IP (testing volume); retries are bounded.

## Open decisions / next steps
- Device tests (APK installs, Kiwix APK vault scan, Kolibri app import, Termux `pip install kolibri`).
- Help text and footer labels are English only.
- After merge, watch the first CI run on GitHub.
