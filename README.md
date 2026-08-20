# Offline Vault 📚⚡

A lightweight, cross-platform offline knowledge manager and synchronization engine designed for **Linux (PC/Server)** and **Android (Termux)**.

Offline Vault allows you to curate, download, update, and serve offline copies of encyclopedias, developer docsets, system administration guides, interactive LMS courses (Kolibri), standalone offline web tools (CyberChef, IT-Tools, CircuitJS1, Draw.io, SQLime, Ptable, MathGrapher, SunCalc, Excalidraw), emergency & survival manuals, multilingual reference materials, maps, and comics with an interactive **Textual TUI** featuring real-time disk budget trade-off calculations.

---

## 🌟 Key Features

- **Interactive Textual TUI**:
  - Live storage budget meter showing available mount space, total selected size, and projected remaining space.
  - Granular selection: toggle individual resources or entire categories with the spacebar.
  - Fast search and filtering by tag, language (`lang:bs`, `lang:es`, `lang:ar`), category (`admin`, `dev`, `tutorials`, `wiki`, `survival`, `maps`, `qna`, `fun`, `tools`), format (`zim`, `kolibri`, `docset`, `epub`, `map`, `zip`, `tar`), or keyword.
- **Categorized Folder Hierarchy**:
  - Files are automatically routed into 9 dedicated category directories matching the TUI:
    `admin/`, `dev/`, `tutorials/`, `wiki/`, `survival/`, `maps/`, `qna/`, `fun/`, `tools/`
- **Dynamic Latest Version Resolution & Canonical Versionless Naming**:
  - Automatically queries upstream indexes (Kiwix XML, Kapeli mirrors, GitHub releases) to fetch the newest releases.
  - Local filenames are clean and versionless (e.g. `xkcd_complete_comics.zim`, `archwiki_en.zim`) so reader app bookmarks never break on updates.
  - Safe atomic update: old versions are safely pruned **only after** the new version downloads successfully.
- **Interactive Offline Web Tools (`tools/`)**:
  - Automatically extracts web apps and creates ready-to-run `index.html` entrypoints for in-browser use.
- **Interactive LMS (Kolibri) Integration**:
  - Supports **Kolibri Learning Management System** courses (PhET simulations, Khan Academy STEM, Sikana vocational trades, CK-12 flexbooks).
  - Launch with 1-click via `offline-vault serve --kolibri`.
- **High-Throughput Resumable Download Engine**:
  - Real-time live streaming progress and speed reporting via `aria2c` (`-s 4 -x 4 -k 1M -c`).
  - Automatic fallback to native Python streaming downloader with HTTP Range header resume support.
  - Atomic file writes (`.new.tmp` → verified target file).

---

## 🧰 Standalone Offline Web Tools Matrix (`tools/`)

All interactive tools are extracted into `<vault>/tools/<tool_id>/` and can be opened in any web browser or served via `offline-vault serve`:

| Tool | ID | Format | Size | Description |
| :--- | :--- | :--- | :--- | :--- |
| **CyberChef** | `cyberchef_suite` | `.zip` | ~75 MB | The Cyber Swiss Army Knife: encryption, decoding, regex, binary analysis |
| **IT-Tools** | `it_tools_suite` | `.zip` | ~40 MB | 80+ client-side utilities: CIDR subnet calc, chmod, cron, JWT, JSON/YAML |
| **CircuitJS1** | `circuitjs_simulator` | `.tar` | ~15 MB | Falstad real-time electronic circuit simulator (op-amps, 555, RLC, logic) |
| **Draw.io** | `drawio_offline_suite` | `.tar` | ~65 MB | Offline diagramming: cloud architectures, network topologies, UML, schematics |
| **SQLime** | `sqlime_sqlite_studio` | `.tar` | ~12 MB | In-browser SQLite WASM database studio & SQL query runner |
| **Ptable** | `ptable_periodic_interactive` | `.tar` | ~12 MB | Dynamic interactive periodic table with 3D electron orbitals & isotopes |
| **MathGrapher** | `geogebra_math_grapher` | `.tar` | ~25 MB | Interactive 2D/3D calculus & algebra function plotting suite |
| **SunCalc** | `suncalc_solar_planner` | `.tar` | ~5 MB | Solar position, azimuth, shadow angles & ephemeris calculator |
| **Excalidraw** | `excalidraw_whiteboard` | `.tar` | ~35 MB | Virtual whiteboard for hand-drawn system sketching & architecture drafts |

---

## 📱 Android Reader Apps Guide

When running Offline Vault on Android (or copying your offline vault from PC to Android storage at `/sdcard/Download/offline_vault/`), use the following recommended open-source apps to view each format:

| Content Type | Format | Recommended Android App | Download Source | Folder Location in Vault |
| :--- | :--- | :--- | :--- | :--- |
| **Encyclopedias & Wikis** | `.zim` | **Kiwix Mobile** | [F-Droid](https://f-droid.org/packages/org.kiwix.kiwixmobile/) / [Google Play](https://play.google.com/store/apps/details?id=org.kiwix.kiwixmobile) | `<vault>/wiki/`, `<vault>/admin/`, `<vault>/fun/` |
| **Interactive Courses & STEM** | `kolibri` | **Kolibri Android App** | [F-Droid](https://f-droid.org/packages/org.learningequality.Kolibri/) / [Google Play](https://play.google.com/store/apps/details?id=org.learningequality.Kolibri) | `<vault>/tutorials/kolibri/` |
| **Literature & Books** | `.epub` | **KOReader** / **Librera** | [F-Droid (KOReader)](https://f-droid.org/packages/org.koreader.launcher.fdroid/) | `<vault>/fun/`, `<vault>/tutorials/` |
| **Offline Vector Maps** | `.map` | **OsmAnd** / **Cruiser** | [F-Droid (OsmAnd~)](https://f-droid.org/packages/net.osmand.plus/) | `<vault>/maps/` |
| **Developer Docsets & HTML** | `.tgz` / `.html` | **Awh** / **Mobile Browser** | [F-Droid (Awh)](https://f-droid.org/packages/de.fe1k.awh/) or `offline-vault serve` | `<vault>/dev/`, `<vault>/admin/` |
| **Offline Web Apps & Tools** | `.html` / `.zip` | **Chrome / Firefox / Browser** | Direct file URL or `offline-vault serve` | `<vault>/tools/<tool_id>/index.html` |

### Setting Up Kiwix on Android:
1. Install **Kiwix Mobile** from F-Droid or Play Store.
2. Open Kiwix, tap **Menu ☰** → **Device Storage** / **Add ZIM file**.
3. Select your vault folder (e.g. `/sdcard/Download/offline_vault/` or individual `.zim` files in `wiki/`, `admin/`, `fun/`).

### Setting Up Kolibri on Android:
1. Install **Kolibri Android App** from F-Droid or Play Store.
2. Launch Kolibri and complete the offline device setup.
3. To load courses:
   - **Local Import**: Select **Device** → **Channels** → **Import** → select folder `/sdcard/Download/offline_vault/tutorials/kolibri/`.
   - **Peer-to-Peer Sync**: If your PC is running `offline-vault serve --kolibri` on the same Wi-Fi network / hotspot, tap **Import from Local Network** to sync courses directly from PC to phone without internet!

---

## 💻 Linux Desktop Reader Apps Guide

| Content Type | Recommended Desktop Tool | How to View / Open |
| :--- | :--- | :--- |
| **Kiwix ZIM Files** | **Kiwix Desktop** or `kiwix-serve` | Run `offline-vault serve --kiwix` and open `http://localhost:8000` |
| **Kolibri LMS Courses** | **Kolibri Local Server** | Run `offline-vault serve --kolibri` and open `http://localhost:8080` |
| **Interactive Web Tools** | **Web Browser** / `offline-vault serve` | Open `<vault>/tools/<tool_id>/index.html` or `http://localhost:8000/tools/` |
| **Developer Docsets** | **Zeal** / **Dash** | Add `<vault>/dev/` docsets to Zeal (`Tools > Docsets > Installed`) |
| **EPUB Classics** | **Foliate** / **Calibre** | Open `.epub` files in `<vault>/fun/` |
| **Vector Maps** | **Cruiser** / **QGIS** | Open `.map` vector files in `<vault>/maps/` |

---

## 🚀 Quick Start (Zero-Setup 1-Click Launcher)

Clone the repository and run `./run.sh` — it will **automatically create and configure the `.venv` and dependencies on first launch**:

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

# 2. Install Python & recommended tools
pkg install -y python aria2 kiwix-tools

# 3. Clone and launch
git clone https://github.com/Adrixan/mobile-encyclopedia.git
cd mobile-encyclopedia
./run.sh
```

---

## 🖥️ Usage

### Launch Interactive TUI (Recommended)
```bash
offline-vault
# or
offline-vault tui
```

#### TUI Keyboard Shortcuts:
| Key | Action |
| :--- | :--- |
| `Space` | Toggle selected resource on/off |
| `S` | Start downloading / synchronizing selected resources |
| `P` | Change Vault Storage Path (Presets: `~/offline_vault`, `/sdcard/Download/offline_vault`) |
| `H` / `?` | Open built-in Help & Reader Guide |
| `A` | Select all currently visible resources |
| `C` | Clear all selections |
| `F` / `/` | Focus search / filter bar |
| `Q` | Quit application |

---

### Non-Interactive CLI Automation

```bash
# List all available resources
offline-vault list

# List with category, language, or format filter
offline-vault list --category tools
offline-vault list --category tutorials
offline-vault list --language bs

# Check vault status and downloaded items
offline-vault status

# Sync specific resources or entire categories
offline-vault sync --category tools
offline-vault sync --id cyberchef_suite --id it_tools_suite --id circuitjs_simulator

# Force update and prune old versions
offline-vault sync --force --id cyberchef_suite

# Launch local servers across LAN/Wi-Fi
offline-vault serve --static    # Multi-threaded portal & web apps server at http://localhost:8000
offline-vault serve --kolibri   # Starts Kolibri LMS at http://localhost:8080
offline-vault serve --kiwix     # Starts Kiwix ZIM server at http://localhost:8000
offline-vault serve --host 0.0.0.0 --port 8080   # Custom host and port for intranet hotspot sharing
```

---

## ⚙️ Configuration

Configuration is stored in `~/.config/offline-vault/config.yaml`:

```yaml
vault_dir: /home/user/offline_vault   # or /sdcard/Download/offline_vault on Termux
locale: en
max_concurrent_downloads: 2
prefer_aria2: true
aria2_split_connections: 4
enable_kiwix_indexing: true
```

---

## 🧪 Running Tests

```bash
pytest tests/
```
