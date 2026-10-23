# Project State

## Environment
- **Target Platforms**: Linux PC (openSUSE, Debian, Arch, Fedora, Ubuntu) & Android Termux (ARM64 / x86_64)
- **Core Language/Runtime**: Python 3.13 (Python 3.10+)
- **Virtual Environment**: `./.venv` with automated 1-click bootstrap via `./run.sh`
- **Installed Packages**: `offline-vault` (0.1.0), `pyyaml`, `textual`, `rich`, `requests`, `pytest`
- **System Tools**: `aria2c`, `kiwix-tools` (optional), `kolibri` (optional)
- **Local Serving / Consumption**: Kiwix (`kiwix-serve`), Kolibri LMS (`offline-vault serve --kolibri`), Static HTTP server (`offline-vault serve --static`)

## User Profile
- **Level**: Senior Systems Engineer / Developer
- **Delivered**:
  - Interactive Textual TUI with real-time dynamic storage budget trade-off meter.
  - Granular resource selection, instant search/filter, and vault path switcher (`P`) with quick presets (`~/offline_vault`, `/sdcard/Download/offline_vault`).
  - Built-in in-app **Help & Reader Guide** modal (`H` / `?`).
  - Multi-stream high-throughput downloader (`aria2c` line-streaming + Python streaming fallback with HTTP Range resume).
  - Typed upstream sources (`kiwix` name+flavour, `github` release asset, `kolibri` channel, `url`) resolving to the latest release; Kiwix index cached 24 h.
  - Canonical versionless names, manifest-based skip/update, signature + SHA-256 verification, staged atomic installs; no deletion outside an item's own path.
  - Catalog with **134 resources across 10 categories** (Sprint 7 added German, infosec, outdoors, books, IF, apps); every one usable on Android (generated from live upstream data on 2026-10-23). Sprint 6 baseline:
    1. **`admin/`**: ArchWiki, Gentoo Wiki, Termux Wiki (ZIM), Debian Administrator's Handbook (EPUB), PowerShell (DevDocs ZIM).
    2. **`dev/`**: DevDocs ZIMs for Python, Rust, C, C++, Go, PHP, JavaScript, HTML, CSS, Web APIs, HTTP, Node.js, PostgreSQL, SQLite, Docker, nginx, Apache; Pro Git (EPUB); OWASP Cheat Sheets (prebuilt site).
    3. **`tutorials/`**: freeCodeCamp, PhET (EN, AR), Khan Academy EN/ES/FR (2023 ZIMs, 96 to 172 GB), TED-Ed (ZIMs); CK-12 (Kolibri channel).
    4. **`wiki/`**: Wikipedia EN top/full-nopic, WikiMed, ES/FR/AR top, BS/HR/SL full, SR full-nopic, Wiktionary ES and SH.
    5. **`survival/`**: Sikana (Kolibri), iFixit, WikEM, Appropedia, CD3WD, Gardenology, Amateur Radio Q&A, LibreTexts Engineering and Mathematics.
    6. **`maps/`**: Austria Mapsforge `.map`, Austria Kiwix map ZIM.
    7. **`qna/`**: Stack Overflow (complete, 110 GB), Unix & Linux, Ask Ubuntu.
    8. **`fun/`**: StoryWeaver (Kolibri), Project Gutenberg LCC P, Bosnian Wikisource, xkcd, SMBC.
    9. **`tools/`**: CyberChef, IT-Tools (own port), draw.io, CircuitJS1, SQLime, GeoGebra; all prebuilt.
  - Non-interactive CLI automation commands (`list`, `status`, `sync`, `serve`).
  - Documentation in `README.md` and the TUI help for Android apps (Kiwix, KOReader, Locus Map, OruxMaps, Kolibri) and Termux serving.

## Sprint History
- **Sprint 0**: Requirements Gathering, User Profiling & Domain Architecture (Done)
- **Sprint 1**: Storage Management (US1.1), Master Catalog & Validator (US2.1), Downloader Engine (US3.1) (Done: 13 pts)
- **Sprint 2**: Interactive Textual TUI (US4.1), CLI Automation & Kiwix / Static Serving (US5.1) (Done: 8 pts)
- **Sprint 3**: Zero-setup bootstrap (`run.sh`), Vault Category Routing, TUI Path Dialog, Live Download Speed Streaming (Done: 8 pts)
- **Sprint 4**: Dynamic Version Resolution, Canonical Versionless Naming, Safe Atomic Pruning, Kolibri LMS Integration, Android Reader Matrix, and Dedicated Standalone Tools Suite (Done: 18 pts)
- **Sprint 5**: Cross-Platform Local Serving Architecture, WASM MIME types, Threading Server with Address Reuse & Intranet Portal Dashboard (Done: 5 pts)
- **Sprint 6**: Android-first catalog v2 (69 real items: Kiwix ZIMs incl. DevDocs, prebuilt web apps, Kolibri channels), safe sync engine (manifest, signature + SHA-256 checks, safe extraction, no collateral pruning), Kolibri import, root-served apps (Done: 16 pts)
- **Sprint 7**: Tool replacements (Excalidraw, Drawnix via `oci`; periodic table; Astronomy Engine), `apps` category with APKs (`fdroid` source), personal material (German, infosec, outdoors, stoics, IF), phone starter set (`--tag starter`, ~14 GB) (Done: 11 pts)
- **Sprint 8**: Catalog-defined privacy/language patches (Excalidraw, Drawnix, periodic table), localhost-only static/Kiwix/Kolibri servers (Done: 5 pts)
- **Total Velocity Delivered**: 84 Story Points. 113 automated tests passing.
- **Catalog maintenance**: `scripts/catalog_spec.yaml` is the source of truth; `scripts/generate_catalog.py` regenerates `src/offline_vault/data/catalog.yaml` from live upstream data (see README "Maintaining the Catalog"). Catalog: 134 items, 114 of them <= 2 GB.
