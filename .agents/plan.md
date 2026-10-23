# Product Backlog & Plan

## Epics & User Stories

### Epic 1: Configuration & Vault Storage Management
- **US1.1: Configurable Vault Directory & Disk Space Inspection** (Must Have, 3 pts) — **DONE**
  - *Story*: As a user on PC or Termux, I want to specify my offline vault directory and see real-time free disk space, so that I can manage my storage safely across mobile partitions and external drives.
  - *Acceptance Criteria*:
    1. System accepts `--vault-dir <path>` or interactive path configuration, saving to `~/.config/offline-vault/config.yaml`.
    2. Path is validated and normalized; creates directories safely.
    3. Calculates and reports available free space on the target mount point via `shutil.disk_usage`.
    4. **(Mandatory Security)** Strict path sanitization preventing path traversal outside the configured root.
    5. **(Mandatory Security)** Restricts configuration file permissions (0600 / 0700).

### Epic 2: Declarative Knowledge Catalog
- **US2.1: Comprehensive YAML Resource Catalog & Registry** (Must Have, 5 pts) — **DONE**
  - *Story*: As a user, I want a categorized YAML catalog containing all confirmed resources (Distro & Admin, Dev Docs & Tutorials, Multilingual Wikis, Survival & Engineering, Maps, Comics, Tools), so that I can filter, inspect, and select exact items to download.
  - *Acceptance Criteria*:
    1. `catalog.yaml` defines metadata: `id`, `name`, `category`, `language`, `format` (`zim`, `docset`, `map`, `epub`, `html`, `kolibri`, `zip`, `tar`), `size_mb`, `upstream_url`, and `tags`.
    2. Covers all 9 confirmed domains across 8 languages (EN, ES, BS, HR, SR, SL, FR, AR).
    3. **(Mandatory Security)** Strict schema validation preventing injection, prototype tampering, or invalid URI protocols (HTTPS only).

### Epic 3: High-Throughput Resumable Download Engine
- **US3.1: Resumable Multi-backend Downloader with Verification** (Must Have, 5 pts) — **DONE**
  - *Story*: As a user, I want fast, resumable, and chunked downloads using `aria2c` (with automatic Python fallback), so that large multi-GB downloads succeed over unstable mobile or home internet.
  - *Acceptance Criteria*:
    1. Checks for `aria2c` binary; invokes optimized multi-connection downloading (`-s 4 -x 4 -k 1M -c`).
    2. Gracefully falls back to pure Python streaming downloader with HTTP Range header support if `aria2c` is not installed.
    3. Downloads write to `.new.tmp` / `.part` and atomically rename on completion.
    4. Validates downloaded file size and integrity.
    5. **(Mandatory Security)** Subprocess invocation uses argument vectors (no `shell=True`) to prevent command injection.

### Epic 4: Interactive Textual TUI
- **US4.1: Visual Resource Browser & Real-Time Storage Budget Meter** (Must Have, 5 pts) — **DONE**
  - *Story*: As a user, I want an interactive Textual TUI to browse categories, toggle resources with checkboxes, compare total size against available disk space in real time, and start downloads, so that I can easily make trade-offs.
  - *Acceptance Criteria*:
    1. Visual tree/table showing categories, items, languages, formats, and sizes.
    2. Dynamic storage budget gauge showing Total Free Space, Selected Size, and Projected Remaining Space.
    3. Live search/filter by language, category, or keyword.
    4. Top bar vault location selector (`P`) with presets and top bar help button (`H` / `?`).
    5. Download screen showing real-time progress bars, speed, ETA, and success indicators.
    6. **(Mandatory Accessibility)** Full keyboard navigation (Tab, Arrow keys, Space to toggle, Enter to start, 'q' to quit).
    7. **(Mandatory Accessibility)** WCAG 2.1 AA compliant color contrast, distinct focus rings, clear keyboard shortcuts bar.

### Epic 5: Local Serving & Integration
- **US5.1: Kiwix, Kolibri LMS & Local Reader Server Integration** (Should Have, 3 pts) — **DONE**
  - *Story*: As a user, I want an automated way to register downloaded ZIM files with Kiwix and start a local web server (Kiwix, Kolibri LMS, or static HTTP), so that I can instantly read offline articles and docsets.
  - *Acceptance Criteria*:
    1. Generates and updates `library.xml` via `kiwix-manage` whenever ZIMs are added.
    2. CLI provides `serve --kolibri`, `serve --kiwix`, and `serve --static`.
    3. Serves interactive web tools directly at `http://localhost:8000/tools/<tool_id>/`.

### Epic 6: Dynamic Upstream Resolution & Standalone Offline Tools Suite
- **US6.1: Dynamic Latest Version Resolution & Canonical Versionless Naming** (Must Have, 5 pts) — **DONE**
  - *Story*: As a user, I want the system to automatically discover and download the latest available dumps and name them versionless locally, so my reader bookmarks and apps never break when updating.
  - *Acceptance Criteria*:
    1. Dynamically parses Kiwix XML and GitHub releases to find the newest release.
    2. Canonical versionless filenames (`<id>.<format>`).
    3. Safe atomic update: old versions pruned only after successful new download.

- **US6.2: Standalone Offline Web Applications & Tools Suite (`tools/`)** (Must Have, 5 pts) — **DONE**
  - *Story*: As a user, I want a dedicated `tools/` category with standalone offline web apps (CyberChef, IT-Tools, CircuitJS1, Draw.io, SQLime, Ptable, MathGrapher, SunCalc, Excalidraw) automatically extracted with `index.html` entrypoints, so that I have offline utility software without running backends.
  - *Acceptance Criteria*:
    1. Dedicated `tools/` category and directory.
    2. Safe archive unpacking (ZipSlip and path traversal protection).
    3. Recursive `index.html` entrypoint discovery and linking.

### Epic 8: Android-First Catalog v2 & Safe Sync (2026-10-23)
Decisions (Peter, 2026-10-23): Kolibri items switch to ZIMs where a ZIM exists; docsets stay Kapeli only if usable on Termux/Android, otherwise ZIMs; tools use prebuilt releases only. Every item must be usable on Android, either in Termux or through an Android app reading the vault folder.
- **US8.1: Safe Sync Engine** (Must Have, 5 pts) — **DONE**
  1. Pruning touches only exact, id-owned paths; other catalog items are never deleted.
  2. Archives extract into a staging dir with path, link and size checks (no symlinks, no `..`, no absolute paths), then swap atomically.
  3. Downloads are validated by file signature per format and by SHA-256 where upstream publishes one (Kiwix `.sha256`, GitHub asset digests); HTML error pages are rejected.
  4. A manifest (`<vault>/.offline-vault/manifest.json`) records url, sha256 and size; items are skipped when current and updated when upstream changed.
  5. One failing item never aborts the batch; aria2 partials are discarded before the Python fallback.
- **US8.2: Catalog v2 with Typed Sources** (Must Have, 5 pts) — **DONE**
  1. Sources `kiwix` (book name + flavour, latest by date), `github` (latest release asset by pattern), `url`, `kolibri` (Studio channel id).
  2. Docsets replaced by DevDocs ZIMs (Kapeli runs on Android only via Zeal under Termux:X11).
  3. Tools are prebuilt web apps with explicit entrypoints; items without a prebuilt are removed.
  4. No placeholder or duplicate URLs; sizes match upstream.
  5. Web apps that need a site root (`serve_root: true`, IT-Tools) get a dedicated port with SPA fallback.
- **US8.3: Kolibri Channel Import** (Should Have, 3 pts) — **DONE**
  1. `kolibri manage importchannel/importcontent network <id>` with `KOLIBRI_CONTENT_DIR=<vault>/tutorials/kolibri/KOLIBRI_DATA/content`, so the vault folder doubles as a Kolibri "local drive" export.
  2. `KOLIBRI_HOME` stays in local app storage (SQLite is unreliable on Android shared storage).
- **US8.4: Android Access Paths** (Must Have, 3 pts) — **DONE**
  1. README and in-app help document per format: Android app reading the vault folder, or Termux server plus browser.
  2. Portal links tools by entrypoint and Kolibri/Kiwix by the current host instead of `localhost`.

### Epic 9: Tool Replacements, Personal Material & Phone Starter Set (2026-10-23)
- **US9.1: Replacements for removed tools** (Must Have, 3 pts) — **DONE**
  1. Excalidraw and Drawnix from the top layer of their official Docker Hub images (`oci` source, layer SHA-256 verified).
  2. Ptable replaced by Future-Style Periodic Table (prebuilt gh-pages); SunCalc by Astronomy Engine browser demos plus Trail Sense APK.
  3. All tools verified in a browser with every external host blocked.
- **US9.2: Android apps in the vault** (Should Have, 3 pts) — **DONE**
  1. `apps` category, `apk` format; `fdroid` source (suggested version); GitHub APKs carry digests.
- **US9.3: Personal offline material** (Should Have, 3 pts) — **DONE**
  1. German references and teaching material, infosec and privacy, outdoors and survival, astronomy, stoic and sci-fi EPUBs, interactive fiction (`z5`/`z8`), hiking map (OpenAndroMaps Austria).
- **US9.4: Phone starter set** (Should Have, 2 pts) — **DONE**
  1. 60 items tagged `starter` (about 14 GB); `list`/`sync --tag`; giants (>20 GB) must say so in their description.

### Epic 10: Privacy Patches, English Defaults, Localhost-Only Serving (2026-10-23)
- **US10.1: Catalog-defined patches** (Must Have, 3 pts) — **DONE**
  1. `patches` (file glob, regex, replacement) applied in staging before the swap; a non-matching patch fails the install and keeps the previous version.
  2. Patch fingerprint in the manifest: changed patches trigger a reinstall.
  3. Excalidraw: Simple Analytics script, CDN asset path, CDN font preloads and CSS CDN font sources removed. Drawnix: Umami removed, English seeded. Periodic table: English initial state.
- **US10.2: Localhost-only servers** (Must Have, 2 pts) — **DONE**
  1. Static portal, root-app ports, kiwix-serve (`--address`) and Kolibri (`KOLIBRI_LISTEN_ADDRESS`) bind to loopback; non-loopback `--host` is rejected (exit 2).
  2. LAN and hotspot sharing removed from docs and portal.
