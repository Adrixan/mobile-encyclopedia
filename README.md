# Offline Vault 📚⚡

A lightweight, cross-platform offline knowledge manager and synchronization engine designed for **Linux (PC/Server)** and **Android (Termux)**.

Offline Vault allows you to curate, download, update, and serve offline copies of encyclopedias, developer docsets, system administration guides, emergency & survival manuals, multilingual reference materials, maps, and comics with an interactive **Textual TUI** featuring real-time disk budget trade-off calculations.

---

## 🌟 Key Features

- **Interactive Textual TUI**:
  - Live storage budget meter showing available mount space, total selected size, and projected remaining space.
  - Granular selection: toggle individual resources or entire categories with the spacebar.
  - Fast search and filtering by tag, language (`lang:bs`, `lang:es`, `lang:ar`), category (`admin`, `dev`, `wiki`, `survival`, `maps`, `fun`), or keyword.
- **Curated Master Knowledge Catalog**:
  - **Linux & System Admin**: openSUSE Admin & Wiki docs, ArchWiki, Debian Administrator's Handbook, Linux Hardening/CIS, Windows Server & PowerShell reference, Sysinternals.
  - **Languages & Databases**: Python 3, Rust, C/C++ (cppreference), Go, PHP, JavaScript, Node.js, PostgreSQL, SQLite, Nginx, Apache, Docker, Pro Git.
  - **Developer Tutorials**: javascript.info, MDN Learn Web Development, FreeCodeCamp curriculum.
  - **Multilingual Encyclopedias (8 Languages)**: English (`en`), Spanish (`es`), Bosnian (`bs`), Croatian (`hr`), Serbian (`sr`), Slovenian (`sl`), French (`fr`), Arabic (`ar`) — Wikipedia (mini/nopic/maxi), Wiktionary, and WikiMed.
  - **Survival & Practical**: WikiHow, iFixit repair guides, Where There Is No Doctor, CD3WD / Appropedia, Ham Radio Emergency Manual, Food Preservation (USDA/FAO), WHO Water Sanitation, Engineering ToolBox, Paul's Math Notes.
  - **Geospatial & Navigation**: OpenStreetMap Mapsforge vector maps (.map), Global City Directory.
  - **Community Q&A**: Stack Overflow (Top 1M), Unix & Linux Stack Exchange, Ask Ubuntu.
  - **Literature & Entertainment**: Standard Ebooks Classics, Multilingual Literature, XKCD Complete Comics, SMBC Webcomics, Classic Interactive Fiction.
- **High-Throughput Resumable Download Engine**:
  - Optimized multi-stream downloads via `aria2c` (`-s 4 -x 4 -k 1M -c`).
  - Automatic fallback to native Python streaming downloader with HTTP Range header resume support.
  - Atomic file writes (`.download.tmp` → verified target file).
- **Offline Readers & Serving**:
  - Automated Kiwix `library.xml` indexing via `kiwix-manage`.
  - Built-in `offline-vault serve` command for `kiwix-serve` or static HTTP hosting.
- **Security & Privacy**:
  - Strict HTTPS enforcement.
  - Safe subprocess argument vectors (no shell interpolation).
  - Strict path sanitization and restricted configuration permissions (`0600`).

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
| `P` | Change Vault Storage Path |
| `A` | Select all currently visible resources |
| `C` | Clear all selections |
| `F` / `/` | Focus search / filter bar |
| `Q` | Quit application |

---

### Non-Interactive CLI Automation

```bash
# List all available resources
offline-vault list

# List with category or language filter
offline-vault list --category admin
offline-vault list --language bs

# Check vault status and disk space
offline-vault status

# Sync specific resources or categories
offline-vault sync --category dev
offline-vault sync --language es
offline-vault sync --id opensuse_wiki_docs --id python_docset

# Launch local Kiwix or static doc server
offline-vault serve --port 8080
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
