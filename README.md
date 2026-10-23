# Offline Vault 📚⚡

A lightweight, cross-platform offline knowledge manager for **Linux (PC/Server)** and **Android (Termux)**.

Offline Vault curates, downloads, verifies, updates and serves offline copies of encyclopedias, developer references (DevDocs), system administration wikis, courses (Kiwix ZIMs and Kolibri channels), prebuilt offline web tools (CyberChef, IT-Tools, draw.io, CircuitJS1, SQLime, GeoGebra), health, repair and survival manuals, multilingual references, maps, books and comics, with an interactive **Textual TUI** featuring a live disk budget meter.

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
  - `url`: a fixed HTTPS download.
- **Verified downloads**:
  - File signature check per format (ZIM, ZIP/EPUB, tar, Mapsforge): HTML error pages are rejected instead of being saved.
  - SHA-256 verification wherever upstream publishes it (Kiwix `.sha256` files, GitHub release asset digests).
  - `aria2c` multi-connection downloads (follows Kiwix metalinks: mirrors plus aria2's own hash checks), with a clean fallback to a resumable Python downloader.
- **Safe, atomic updates**:
  - Canonical versionless names (`wiki/wikipedia_en_top.zim`, `tools/cyberchef_suite/`) so reader bookmarks survive updates.
  - A manifest (`<vault>/.offline-vault/manifest.json`) records URL, checksum and size: unchanged items are skipped, items with a newer upstream release are updated.
  - Files are replaced only after a verified download; web apps are extracted into a staging folder and swapped in. Nothing outside an item's own path is ever deleted.
  - Archive extraction drops symlinks, device files, absolute paths and `..` traversal, and checks free space first.
- **Local serving for phones, tablets and PCs**: static portal and web apps, Kiwix (`kiwix-serve`), Kolibri.

---

## 📂 Vault Layout

```
<vault>/
├── admin/ dev/ wiki/ survival/ maps/ qna/ fun/   *.zim, *.epub, *.map, extracted sites
├── tutorials/
│   └── kolibri/KOLIBRI_DATA/content/             Kolibri channels (export-compatible layout)
├── tools/<tool_id>/index.html                    prebuilt offline web apps
├── library.xml                                   Kiwix library (rebuilt after ZIM changes)
├── index.html                                    portal written by `offline-vault serve`
└── .offline-vault/manifest.json                  what is installed, from where, with which checksum
```

---

## 🧰 Prebuilt Offline Web Tools (`tools/`)

Only prebuilt, deployable releases are used; nothing needs a build step on the phone.

| Tool | ID | Source | Opens at |
| :--- | :--- | :--- | :--- |
| **CyberChef** | `cyberchef_suite` | latest GitHub release ZIP | `tools/cyberchef_suite/` |
| **IT-Tools** | `it_tools_suite` | latest GitHub release ZIP | its own port (`http://localhost:8001` when the portal runs on 8000) |
| **draw.io** | `drawio_offline_suite` | latest GitHub release `draw.war` | `tools/drawio_offline_suite/index.html?offline=1` |
| **CircuitJS1** | `circuitjs_simulator` | web build from Falstad's official offline bundle | `tools/circuitjs_simulator/circuitjs.html` |
| **SQLime** | `sqlime_sqlite_studio` | repository = static site (SQLite WebAssembly bundled) | `tools/sqlime_sqlite_studio/` |
| **GeoGebra** | `geogebra_math_apps` | official GeoGebra Math Apps bundle (free for non-commercial use) | `tools/geogebra_math_apps/` |

IT-Tools is a single-page app that only works at a site root, so `offline-vault serve` gives it a dedicated port. The CircuitJS1 Dropbox button and the OWASP site's web fonts need internet; everything else runs fully offline.

---

## 📱 Android Guide

Grant Termux storage access once (`termux-setup-storage`); the default vault is then `/sdcard/Download/offline_vault`, which Android apps can open.

| Content | Format | How to use it on Android | Vault folder |
| :--- | :--- | :--- | :--- |
| Encyclopedias, wikis, DevDocs, Q&A, courses, comics | `.zim` | **Kiwix** app ([Play Store](https://play.google.com/store/apps/details?id=org.kiwix.kiwixmobile), [APK](https://download.kiwix.org/release/kiwix-android/)), or Termux `offline-vault serve --kiwix` plus the browser | all categories |
| Books | `.epub` | **KOReader** ([F-Droid](https://f-droid.org/packages/org.koreader.launcher.fdroid/)) | `admin/`, `dev/` |
| Vector maps | `.map` | **Locus Map** ([Play Store](https://play.google.com/store/apps/details?id=menion.android.locus)) or **OruxMaps** ([oruxmaps.com](https://www.oruxmaps.com/)): import as Mapsforge offline map | `maps/` |
| Web apps and extracted sites | folder | Termux `offline-vault serve`, then open `http://localhost:8000` in the browser | `tools/`, `dev/owasp_cheat_sheet_series/` |
| Kolibri channels | `KOLIBRI_DATA` | **Kolibri** app ([Play Store](https://play.google.com/store/apps/details?id=org.learningequality.Kolibri), [APK](https://github.com/learningequality/kolibri/releases/latest)): import channels from the folder or from a PC on the same Wi-Fi; or Termux `offline-vault serve --kolibri` | `tutorials/kolibri/` |

**Kiwix:** the Play Store build opens ZIMs through the system file picker (Android storage rules); the APK from download.kiwix.org can scan the vault folder directly.

**Kolibri:** syncing a Kolibri item needs the `kolibri` command (`pip install kolibri`, also inside Termux). Content is written in the layout Kolibri's "import from drive" expects, so the same folder can be imported by the Kolibri app or by another device. Kolibri's own database stays in `~/.local/share/offline-vault/kolibri-home` because SQLite is unreliable on Android shared storage.

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

# 3. Optional: Kolibri for Kolibri channels
pip install kolibri

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
offline-vault list --category tools             # filters: --category, --language, --format, --query
offline-vault status                            # vault path, free space, installed items
offline-vault status --vault-dir /sdcard/Download/offline_vault

offline-vault sync --category tools             # download missing or outdated items
offline-vault sync --category wiki --language bs  # filters combine
offline-vault sync --id cyberchef_suite --id devdocs_python
offline-vault sync --force --id cyberchef_suite # re-download even if current

offline-vault serve --static                    # portal + web apps on port 8000 (IT-Tools on 8001)
offline-vault serve --kiwix                     # kiwix-serve on port 8000
offline-vault serve --kolibri                   # Kolibri on port 8080
offline-vault serve --host 127.0.0.1 --port 9000  # bind locally only, custom port
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

## 🧪 Running Tests

```bash
pytest tests/
```
