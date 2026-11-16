# 📚 Offline Knowledge Vault Guide

### ⌨️ Keyboard Controls
- **Space**: Toggle selection of highlighted item
- **S**: Download missing or outdated selected items
- **P**: Set / change vault path (presets: `~/offline_vault`, `/sdcard/Download/offline_vault`)
- **A**: Select all visible resources
- **C**: Clear all selections
- **F** / **/**: Focus search & filter bar (`lang:bs`, `cat:wiki`, `tag:security`)
- **H** / **?**: Open this guide, **Esc** closes it
- **R**: Refresh the catalog (latest versions and sizes from upstream)
- **Q**: Quit

---

### 📂 Formats & Folders
Files keep versionless names, so bookmarks survive updates:
- **`.zim`** (all categories): wikis, DevDocs references, Q&A, courses, comics. Open in Kiwix.
- **`.epub`** (`admin/`, `dev/`): books. Open in KOReader.
- **`.map`** (`maps/`): Mapsforge vector maps. Open in Locus Map or OruxMaps.
- **`tools/<id>/`**: prebuilt web apps (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, periodic table, sun & moon calculators).
- **`.z5` / `.z8`** (`fun/`): interactive fiction. Play with `frotz` in Termux.
- **`apps/*.apk`**: Kiwix, KOReader, Trail Sense, Sky Map, Kolibri for offline installs.
- **`tutorials/kolibri/`**: Kolibri channels (Sikana, CK-12, StoryWeaver). Needs `pip install kolibri`.

**Phone starter set (about 14 GB):** search `tag:starter`, press **A**, then **S**.

---

### 📱 Android
| Content | App | Vault folder |
| :--- | :--- | :--- |
| **`.zim`** | **Kiwix** (Play Store or APK from download.kiwix.org) | any category |
| **`.epub`** | **KOReader** (F-Droid) | `admin/`, `dev/` |
| **`.map`** | **Locus Map** / **OruxMaps** | `maps/` |
| **Web apps** | Browser via `offline-vault serve` in Termux | `tools/` |
| **`.z5` / `.z8`** | `pkg install frotz` in Termux | `fun/` |
| **`.apk`** | File manager: install from file | `apps/` |
| **Kolibri** | **Kolibri** app: import from the vault folder | `tutorials/kolibri/` |

**Kiwix:** the Play Store build opens ZIMs through the file picker; the APK build can scan the vault folder.

**Web apps:** run `offline-vault serve` in Termux and open `http://localhost:8000` in the browser.
IT-Tools, Excalidraw and Drawnix get their own ports (8001, 8002, ...), listed on the portal.

---

### 💻 Local Serving (localhost only)
- `offline-vault serve --static`: portal and web apps at `http://localhost:8000`
- `offline-vault serve --kiwix`: Kiwix server at `http://localhost:8000`
- `offline-vault serve --kolibri`: Kolibri at `http://localhost:8080`
