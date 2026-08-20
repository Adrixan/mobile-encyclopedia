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
  - Granular resource selection, instant search/filter, and vault path switcher (`P`) with quick presets (`~/offline_vault`, `/sdcard/Download/offline_vault`, `/tmp/offline_vault`).
  - Built-in in-app **Help & Reader Guide** modal (`H` / `?`).
  - Multi-stream high-throughput downloader (`aria2c` line-streaming + Python streaming fallback with HTTP Range resume).
  - Dynamic upstream latest-version resolution for Kiwix XML and GitHub release assets.
  - Canonical versionless local naming (`<id>.<format>`) with safe atomic pruning on update.
  - Master catalog with **76 curated resources across 9 clean categories**:
    1. **`admin/`**: openSUSE Admin & Wiki, ArchWiki, Debian Handbook, Windows Server & PowerShell reference, Sysinternals, Linux Hardening.
    2. **`dev/`**: Python 3, Rust, C/C++ (cppreference), Go, PHP, JavaScript (MDN), Node.js, PostgreSQL, SQLite, Docker, Pro Git, Nginx/Apache, Networking RFCs, OWASP Cheat Sheets.
    3. **`tutorials/`**: javascript.info, MDN Learn Web Dev, FreeCodeCamp curriculum, and 11 Kolibri interactive courses (PhET simulations, Khan Academy STEM, Sikana trades, CK-12 flexbooks, TED-Ed, multilingual Khan courses in ES, FR, AR).
    4. **`wiki/`**: Multilingual encyclopedias across 8 languages (EN, ES, BS, HR, SR, SL, FR, AR) — Wikipedia top/full/nopic, Wiktionary, WikiMed.
    5. **`survival/`**: WikiHow, iFixit repair manuals, Where There Is No Doctor, CD3WD/Appropedia, Ham Radio Emergency Handbook, Food Preservation, WHO Water Sanitation, Engineering ToolBox, Paul's Math Notes.
    6. **`maps/`**: OpenStreetMap Mapsforge vector maps (.map), Global World City & Airport Directory.
    7. **`qna/`**: Stack Overflow top answers, Unix & Linux Stack Exchange, Ask Ubuntu.
    8. **`fun/`**: Standard Ebooks top 50, Multilingual Literature Classics, XKCD Complete Comics, SMBC Webcomics, Classic Interactive Fiction.
    9. **`tools/`**: 9 standalone offline web applications: CyberChef, IT-Tools, CircuitJS1 (Falstad), Draw.io (diagrams.net), SQLime (WASM SQLite), Ptable (Interactive Periodic Table), MathGrapher, SunCalc, Excalidraw Whiteboard.
  - Non-interactive CLI automation commands (`list`, `status`, `sync`, `serve`).
  - Comprehensive documentation in `README.md` and TUI for Android reader apps (Kiwix Mobile, Kolibri Android, KOReader, OsmAnd, Awh) and desktop consumption.

## Sprint History
- **Sprint 0**: Requirements Gathering, User Profiling & Domain Architecture (Done)
- **Sprint 1**: Storage Management (US1.1), Master Catalog & Validator (US2.1), Downloader Engine (US3.1) (Done: 13 pts)
- **Sprint 2**: Interactive Textual TUI (US4.1), CLI Automation & Kiwix / Static Serving (US5.1) (Done: 8 pts)
- **Sprint 3**: Zero-setup bootstrap (`run.sh`), Vault Category Routing, TUI Path Dialog, Live Download Speed Streaming (Done: 8 pts)
- **Sprint 4**: Dynamic Version Resolution, Canonical Versionless Naming, Safe Atomic Pruning, Kolibri LMS Integration, Android Reader Matrix, and Dedicated Standalone Tools Suite (Done: 18 pts)
- **Sprint 5**: Cross-Platform Local Serving Architecture, WASM MIME types, Threading Server with Address Reuse & Intranet Portal Dashboard (Done: 5 pts)
- **Total Velocity Delivered**: 52 Story Points. All 43 automated test suites passing (100% green).
