# Product Backlog & Plan

## Epics & User Stories

### Epic 1: Configuration & Vault Storage Management
- **US1.1: Configurable Vault Directory & Disk Space Inspection** (Must Have, 3 pts)
  - *Story*: As a user on PC or Termux, I want to specify my offline vault directory and see real-time free disk space, so that I can manage my storage safely across mobile partitions and external drives.
  - *Acceptance Criteria*:
    1. System accepts `--vault-dir <path>` or interactive path configuration, saving to `~/.config/offline-vault/config.yaml`.
    2. Path is validated and normalized; creates directories safely.
    3. Calculates and reports available free space on the target mount point via `shutil.disk_usage`.
    4. **(Mandatory Security)** Strict path sanitization preventing path traversal outside the configured root.
    5. **(Mandatory Security)** Restricts configuration file permissions (0600 / 0700).

### Epic 2: Declarative Knowledge Catalog
- **US2.1: Comprehensive YAML Resource Catalog & Registry** (Must Have, 5 pts)
  - *Story*: As a user, I want a categorized YAML catalog containing all confirmed resources (Distro & Admin, Dev Docs & Tutorials, Multilingual Wikis, Survival & Engineering, Maps, Comics), so that I can filter, inspect, and select exact items to download.
  - *Acceptance Criteria*:
    1. `catalog.yaml` defines metadata: `id`, `name`, `category`, `language`, `format` (`zim`, `docset`, `map`, `epub`, `html`), `size_mb`, `upstream_url`, and `tags`.
    2. Covers all 8 confirmed domains:
       - Distro & Admin: openSUSE, ArchWiki, Debian Handbook, LDP, Linux Hardening/CIS, Windows Server, PowerShell, Sysinternals.
       - Languages & DBs: Python, Rust, C/C++, Go, PHP, JavaScript, Node.js, PostgreSQL, SQLite, Nginx, Apache, Docker, Git.
       - Tutorials: javascript.info, MDN Learn, FreeCodeCamp.
       - Multilingual: EN, ES, BS, HR, SR, SL, FR, AR (Wikipedia, Wiktionary, WikiMed).
       - Survival & Engineering: WikiHow, iFixit, Medical, CD3WD, Ham Radio, Food Preservation, Water Sanitation, Engineering ToolBox, Math Notes.
       - Geospatial: OSM Mapsforge vector maps (.map), City directory.
       - Q&A: Stack Overflow, Unix & Linux SE, Ask Ubuntu.
       - Entertainment: Standard Ebooks, Multilingual Classics, XKCD, SMBC, Interactive Fiction.
    3. **(Mandatory Security)** Strict schema validation preventing injection, prototype tampering, or invalid URI protocols (HTTPS only).

### Epic 3: High-Throughput Resumable Download Engine
- **US3.1: Resumable Multi-backend Downloader with Verification** (Must Have, 5 pts)
  - *Story*: As a user, I want fast, resumable, and chunked downloads using `aria2c` (with automatic Python fallback), so that large multi-GB downloads succeed over unstable mobile or home internet.
  - *Acceptance Criteria*:
    1. Checks for `aria2c` binary; invokes optimized multi-connection downloading (`-s 4 -x 4 -k 1M -c`).
    2. Gracefully falls back to pure Python streaming downloader with HTTP Range header support if `aria2c` is not installed.
    3. Downloads write to `.download.tmp` / `.part` and atomically rename on completion.
    4. Validates downloaded file size and integrity.
    5. **(Mandatory Security)** Subprocess invocation uses argument vectors (no `shell=True`) to prevent command injection.
    6. **(Mandatory Security)** TLS/HTTPS certificates validated; network timeouts configured.

### Epic 4: Interactive Textual TUI
- **US4.1: Visual Resource Browser & Real-Time Storage Budget Meter** (Must Have, 5 pts)
  - *Story*: As a user, I want an interactive Textual TUI to browse categories, toggle resources with checkboxes, compare total size against available disk space in real time, and start downloads, so that I can easily make trade-offs.
  - *Acceptance Criteria*:
    1. Visual tree/table showing categories, items, languages, formats, and sizes.
    2. Dynamic storage budget gauge showing Total Free Space, Selected Size, and Projected Remaining Space.
    3. Live search/filter by language (`lang:bs`, `lang:ar`, `lang:es`), category (`dev`, `admin`, `wiki`, `survival`, `fun`), or keyword.
    4. Download screen showing real-time progress bars, speed, ETA, and success indicators.
    5. **(Mandatory Accessibility)** Full keyboard navigation (Tab, Arrow keys, Space to toggle, Enter to start, 'q' to quit).
    6. **(Mandatory Accessibility)** WCAG 2.1 AA compliant color contrast, distinct focus rings, clear keyboard shortcuts bar.

### Epic 5: Local Serving & Integration
- **US5.1: Kiwix & Local Reader Server Integration** (Should Have, 3 pts)
  - *Story*: As a user, I want an automated way to register downloaded ZIM files with Kiwix and start a local web server, so that I can instantly read offline articles and docsets.
  - *Acceptance Criteria*:
    1. Generates and updates `library.xml` via `kiwix-manage` whenever ZIMs are added.
    2. CLI/TUI provides a `serve` command to launch `kiwix-serve` or a local static HTTP server.
    3. Clear diagnostics if `kiwix-tools` is missing on Linux or Termux.
