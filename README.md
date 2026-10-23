# Offline Vault 📚⚡

A lightweight, cross-platform offline knowledge manager for **Linux (PC/Server)** and **Android (Termux)**.

Offline Vault curates, downloads, verifies, updates and serves offline copies of encyclopedias (English, German and six more languages), developer references (DevDocs), system administration and infosec material, courses (Kiwix ZIMs and Kolibri channels), prebuilt offline web tools (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, a periodic table, sun and moon calculators), health, repair, outdoor and survival manuals, hiking maps, books, interactive fiction and the Android apps to read it all, with an interactive **Textual TUI** featuring a live disk budget meter.

**Android first:** every catalog item is usable on Android, either through an Android app that reads the vault folder or through Termux (`offline-vault serve` plus the phone's browser).

---

## 🌟 Key Features

- **Interactive Textual TUI**:
  - Live storage budget meter: available mount space, selected size, projected remaining space.
  - Toggle individual resources with Space; select or clear all visible items.
  - Search by keyword or prefix: `lang:bs`, `cat:wiki`, `tag:security`; category buttons for `admin`, `dev`, `tutorials`, `wiki`, `survival`, `maps`, `qna`, `fun`, `tools`.
- **Typed upstream sources, always the latest release**:
  - `kiwix`: picks the newest ZIM of a Kiwix book (name + flavour) from the Kiwix library index (cached for 24 hours to spare mobile data).
  - `github`: picks the newest release asset matching a pattern.
  - `kolibri`: imports a Kolibri Studio channel by its channel ID.
  - `oci`: extracts a web app from the top layer of an official Docker Hub image (layer verified by its SHA-256 digest).
  - `fdroid`: the APK F-Droid currently suggests for a package.
  - `url`: a fixed HTTPS download.
- **Verified downloads**:
  - File signature check per format (ZIM, ZIP/EPUB, tar, Mapsforge): HTML error pages are rejected instead of being saved.
  - SHA-256 verification wherever upstream publishes it (Kiwix `.sha256` files, GitHub release asset digests, Docker layer digests). Set `GITHUB_TOKEN` (or `GH_TOKEN`) to avoid GitHub's anonymous API limit of 60 requests per hour, which otherwise drops asset digests.
  - `aria2c` multi-connection downloads (follows Kiwix metalinks: mirrors plus aria2's own hash checks), with a clean fallback to a resumable Python downloader.
- **Safe, atomic updates**:
  - Canonical versionless names (`wiki/wikipedia_en_top.zim`, `tools/cyberchef_suite/`) so reader bookmarks survive updates.
  - A manifest (`<vault>/.offline-vault/manifest.json`) records URL, checksum and size: unchanged items are skipped, items with a newer upstream release are updated.
  - Files are replaced only after a verified download; web apps are extracted into a staging folder and swapped in. Nothing outside an item's own path is ever deleted.
  - Archive extraction drops symlinks, device files, absolute paths and `..` traversal, and checks free space first.
- **Local serving, localhost only**: static portal and web apps, Kiwix (`kiwix-serve`) and Kolibri listen on `127.0.0.1`; other hosts are refused, so nothing is exposed on Wi-Fi or a hotspot.
- **Privacy patches**: catalog-defined edits applied to upstream web app builds before install (strip analytics, drop CDN font loading, set English defaults). A patch that no longer matches fails the install and keeps the previous version, so a tracker can never silently return after an update.

---

## 📦 Phone Starter Set (about 14 GB)

60 items tagged `starter`, sized for a phone: German and English Wikipedia (text-only editions), Wiktionary DE, Wikivoyage DE, WikiMed, DevDocs (Python, Bash, Git, Ansible, PHP, JavaScript, Docker), ArchWiki, Termux Wiki, OPSEC and privacy guides, OWASP, Security, Crypto and Unix Stack Exchange, outdoors and fitness Q&A, WikEM and field medicine, knots and water treatment, Low-Tech Magazine, the OpenAndroMaps Austria hiking map, stoic classics and dystopian sci-fi, interactive fiction, all web tools and the reader APKs.

```bash
offline-vault list --tag starter            # review the set
offline-vault sync --tag starter            # download it
```

In the TUI, type `tag:starter` in the search bar and press `A` to select the set. 114 of the 134 catalog items are 2 GB or smaller; the few giants (complete English Wikipedia, Stack Overflow, Khan Academy) say so in their description.

---

## 📂 Vault Layout

```
<vault>/
├── admin/ dev/ wiki/ survival/ maps/ qna/ fun/   *.zim, *.epub, *.map, extracted sites
├── tutorials/
│   └── kolibri/KOLIBRI_DATA/content/             Kolibri channels (export-compatible layout)
├── tools/<tool_id>/index.html                    prebuilt offline web apps
├── apps/*.apk                                    Android apps to install without internet
├── library.xml                                   Kiwix library (rebuilt after ZIM changes)
├── index.html                                    portal written by `offline-vault serve`
└── .offline-vault/manifest.json                  what is installed, from where, with which checksum
```

---

## 🧰 Prebuilt Offline Web Tools (`tools/`)

Only prebuilt, deployable builds are used; nothing needs a build step on the phone. All tools below were opened with every internet host blocked.

| Tool | ID | Source | Opens at (portal on port 8000) |
| :--- | :--- | :--- | :--- |
| **CyberChef** | `cyberchef_suite` | latest GitHub release ZIP | `tools/cyberchef_suite/` |
| **IT-Tools** | `it_tools_suite` | latest GitHub release ZIP | own port, `http://localhost:8001` |
| **draw.io** | `drawio_offline_suite` | latest GitHub release `draw.war` | `tools/drawio_offline_suite/index.html?offline=1` |
| **Excalidraw** | `excalidraw_whiteboard` | official Docker image `excalidraw/excalidraw` | own port, `http://localhost:8002` |
| **Drawnix** | `drawnix_whiteboard` | official Docker image `pubuzhixing/drawnix` (whiteboard, mind maps, flowcharts) | own port, `http://localhost:8003` |
| **CircuitJS1** | `circuitjs_simulator` | web build from Falstad's official offline bundle | `tools/circuitjs_simulator/circuitjs.html` |
| **SQLime** | `sqlime_sqlite_studio` | repository = static site (SQLite WebAssembly bundled) | `tools/sqlime_sqlite_studio/` |
| **GeoGebra** | `geogebra_math_apps` | official GeoGebra Math Apps bundle (free for non-commercial use) | `tools/geogebra_math_apps/` |
| **Future-Style Periodic Table** | `periodic_table_cyberpunk` | prebuilt `gh-pages` site (MIT) | `tools/periodic_table_cyberpunk/` |
| **Sun & Moon Calculators** | `astronomy_engine_demos` | Astronomy Engine browser demos (MIT): rise/set, moon phase, planet positions | `tools/astronomy_engine_demos/` |

Apps that only work at a site root (IT-Tools, Excalidraw, Drawnix) get ports 8001, 8002, ... in catalog order among the installed ones; `offline-vault serve` prints them and the portal links them. Privacy and language patches (verified with internet access allowed: no outside requests at startup): Excalidraw has its Simple Analytics script and CDN font loading removed and uses its bundled fonts; Drawnix has its Umami analytics removed and starts in English; the periodic table starts in English (its element photos still load from the web when online). Still needing internet: the CircuitJS1 Dropbox button and the OWASP site's web fonts.

---

## 📱 Android Guide

Grant Termux storage access once (`termux-setup-storage`); the default vault is then `/sdcard/Download/offline_vault`, which Android apps can open.

| Content | Format | How to use it on Android | Vault folder |
| :--- | :--- | :--- | :--- |
| Encyclopedias, wikis, DevDocs, Q&A, courses, comics | `.zim` | **Kiwix** app ([Play Store](https://play.google.com/store/apps/details?id=org.kiwix.kiwixmobile), [APK](https://download.kiwix.org/release/kiwix-android/)), or Termux `offline-vault serve --kiwix` plus the browser | all categories |
| Books | `.epub` | **KOReader** ([F-Droid](https://f-droid.org/packages/org.koreader.launcher.fdroid/)) | `admin/`, `dev/` |
| Vector maps | `.map` | **Locus Map** ([Play Store](https://play.google.com/store/apps/details?id=menion.android.locus)) or **OruxMaps** ([oruxmaps.com](https://www.oruxmaps.com/)): import as Mapsforge offline map | `maps/` |
| Web apps and extracted sites | folder | Termux `offline-vault serve`, then open `http://localhost:8000` in the browser | `tools/`, `dev/owasp_cheat_sheet_series/` |
| Interactive fiction | `.z5` / `.z8` | Termux: `pkg install frotz`, then `frotz <vault>/fun/if_anchorhead.z8`; or any Z-machine interpreter app | `fun/` |
| Android apps | `.apk` | Open the file in a file manager and allow installs from it | `apps/` |
| Kolibri channels | `KOLIBRI_DATA` | **Kolibri** app ([Play Store](https://play.google.com/store/apps/details?id=org.learningequality.Kolibri), [APK](https://github.com/learningequality/kolibri/releases/latest)): import channels from the vault folder; or Termux `offline-vault serve --kolibri` | `tutorials/kolibri/` |

**Kiwix:** the Play Store build opens ZIMs through the system file picker (Android storage rules); the APK from download.kiwix.org can scan the vault folder directly.

**Kolibri:** syncing a Kolibri item needs the `kolibri` command (`pip install kolibri`, also inside Termux). Content is written in the layout Kolibri's "import from drive" expects, so the same folder can be imported by the Kolibri app or by another device. Kolibri's own database stays in `~/.local/share/offline-vault/kolibri-home` because SQLite is unreliable on Android shared storage.

**Apps in the vault (`apps/`):** Kiwix (arm64), KOReader (arm64), Trail Sense (offline sun and moon times, compass, navigation, barometer), Sky Map (F-Droid build) and Kolibri. Keeping them in the vault lets you set up a phone without internet (copy the APK over USB or an SD card for another device). Termux itself is not included: its GitHub builds are debug-signed and cannot be mixed with the F-Droid build.

**Why no Kapeli docsets:** Dash/Zeal docsets only run on Android through Zeal inside a Termux:X11 desktop. The DevDocs ZIMs carry the same documentation, are 1 to 14 MB each and open in Kiwix.

---

## 💻 Linux Desktop Guide

| Content | Tool | How to open |
| :--- | :--- | :--- |
| ZIM files | **Kiwix Desktop** or `kiwix-serve` | `offline-vault serve --kiwix`, then `http://localhost:8000` |
| Kolibri channels | **Kolibri** (`pip install kolibri`) | `offline-vault serve --kolibri`, then `http://localhost:8080` |
| Web apps | Browser | `offline-vault serve --static`, then `http://localhost:8000` |
| EPUB | **Foliate** / **Calibre** | open the `.epub` files |
| Vector maps | **QGIS** (Mapsforge plugin) or any Mapsforge viewer | open `maps/*.map` |

---

## 🚀 Quick Start (Zero-Setup Launcher)

`./run.sh` creates the `.venv` and installs dependencies on first launch:

```bash
git clone https://github.com/Adrixan/mobile-encyclopedia.git
cd mobile-encyclopedia
./run.sh
```

### Installation on Android (Termux)

```bash
# 1. Update Termux packages & grant storage access
pkg update -y && pkg upgrade -y
termux-setup-storage

# 2. Install Python & recommended tools (kiwix-tools and aria2 are Termux packages)
pkg install -y python aria2 kiwix-tools

# 3. Optional: Kolibri for Kolibri channels, frotz for interactive fiction
pip install kolibri
pkg install -y frotz

# 4. Clone and launch
git clone https://github.com/Adrixan/mobile-encyclopedia.git
cd mobile-encyclopedia
./run.sh
```

Install Termux from [F-Droid](https://f-droid.org/packages/com.termux/). For multi-GB downloads keep the screen on or run `termux-wake-lock` first.

---

## 🖥️ Usage

### Interactive TUI (recommended)
```bash
offline-vault        # or: offline-vault tui
```

| Key | Action |
| :--- | :--- |
| `Space` | Toggle the highlighted resource |
| `S` | Download missing or outdated selected resources |
| `P` | Change vault path (presets: `~/offline_vault`, `/sdcard/Download/offline_vault`) |
| `H` / `?` | Help and reader guide (`Esc` closes) |
| `A` | Select all visible resources |
| `C` | Clear all selections |
| `F` / `/` | Focus the search bar |
| `Q` | Quit |

### Non-interactive CLI

```bash
offline-vault list                              # whole catalog
offline-vault list --category tools             # filters: --category, --language, --format, --query, --tag
offline-vault status                            # vault path, free space, installed items
offline-vault status --vault-dir /sdcard/Download/offline_vault

offline-vault sync --category tools             # download missing or outdated items
offline-vault sync --category wiki --language bs  # filters combine
offline-vault sync --tag starter                # the phone starter set
offline-vault sync --id cyberchef_suite --id devdocs_python
offline-vault sync --force --id cyberchef_suite # re-download even if current

offline-vault serve --static                    # portal + web apps on port 8000 (root-only apps on 8001+)
offline-vault serve --kiwix                     # kiwix-serve on port 8000
offline-vault serve --kolibri                   # Kolibri on port 8080
offline-vault serve --port 9000                # custom port; servers always bind to localhost
                                                # (--host accepts only 127.0.0.1, ::1 or localhost)
```

`sync` exits non-zero if any item fails; each failure is listed with its reason. One failing item never stops the rest.

---

## ⚙️ Configuration

`~/.config/offline-vault/config.yaml` (mode 0600):

```yaml
vault_dir: /home/user/offline_vault   # or /sdcard/Download/offline_vault on Termux
prefer_aria2: true
aria2_split_connections: 4
enable_kiwix_indexing: true           # rebuild library.xml with kiwix-manage after ZIM changes
```

---

## 🗂️ Maintaining the Catalog

`src/offline_vault/data/catalog.yaml` is generated; edit `scripts/catalog_spec.yaml` instead. The spec lists each item's typed source (Kiwix book and flavour, GitHub repo and asset pattern, Docker image, F-Droid package, Kolibri channel or URL), its patches, and the `starter:` set. The generator fills `upstream_url` and `size_mb` from live upstream data and fails on anything it cannot resolve.

```bash
GITHUB_TOKEN=$(gh auth token) .venv/bin/python scripts/generate_catalog.py   # --refresh re-downloads indexes
pytest tests/
```

The Kiwix and Kolibri indexes (about 25 MB) are cached for 24 hours in `.scratch/catalog-inputs/` (git-ignored). Pin `size_mb` in the spec for archives whose installed size differs from the download or whose server sends no length. `tests/test_catalog_generator.py` fails if the committed catalog and spec drift apart.

---

## 🧪 Running Tests

```bash
pytest tests/
```
