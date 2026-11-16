# 📚 Anleitung zum Offline Knowledge Vault

### ⌨️ Tastaturbefehle
- **Leertaste**: markierten Eintrag aus- oder abwählen
- **S**: fehlende oder veraltete ausgewählte Einträge herunterladen
- **P**: Vault-Pfad festlegen oder ändern (Vorgaben: `~/offline_vault`, `/sdcard/Download/offline_vault`)
- **A**: alle sichtbaren Einträge auswählen
- **C**: Auswahl aufheben
- **F** / **/**: Such- und Filterleiste fokussieren (`lang:bs`, `cat:wiki`, `tag:security`)
- **H** / **?**: diese Anleitung öffnen, **Esc** schließt sie
- **R**: Katalog aktualisieren (neueste Versionen und Größen aus den Quellen)
- **Q**: beenden

---

### 📂 Formate und Ordner
Dateien tragen keine Versionsnummer im Namen, damit Lesezeichen Updates überstehen:
- **`.zim`** (alle Kategorien): Wikis, DevDocs-Referenzen, F&A, Kurse, Comics. Öffnen in Kiwix.
- **`.epub`** (`admin/`, `dev/`): Bücher. Öffnen in KOReader.
- **`.map`** (`maps/`): Mapsforge-Vektorkarten. Öffnen in Locus Map oder OruxMaps.
- **`tools/<id>/`**: fertig gebaute Web-Apps (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, Periodensystem, Sonnen- und Mondrechner).
- **`.z5` / `.z8`** (`fun/`): Interactive Fiction. Spielen mit `frotz` in Termux.
- **`apps/*.apk`**: Kiwix, KOReader, Trail Sense, Sky Map, Kolibri zur Offline-Installation.
- **`tutorials/kolibri/`**: Kolibri-Kanäle (Sikana, CK-12, StoryWeaver). Braucht `pip install kolibri`.

**Starterpaket fürs Handy (etwa 14 GB):** nach `tag:starter` suchen, **A** drücken, dann **S**.

---

### 📱 Android
| Inhalt | App | Vault-Ordner |
| :--- | :--- | :--- |
| **`.zim`** | **Kiwix** (Play Store oder APK von download.kiwix.org) | jede Kategorie |
| **`.epub`** | **KOReader** (F-Droid) | `admin/`, `dev/` |
| **`.map`** | **Locus Map** / **OruxMaps** | `maps/` |
| **Web-Apps** | Browser über `offline-vault serve` in Termux | `tools/` |
| **`.z5` / `.z8`** | `pkg install frotz` in Termux | `fun/` |
| **`.apk`** | Dateimanager: aus Datei installieren | `apps/` |
| **Kolibri** | **Kolibri**-App: aus dem Vault-Ordner importieren | `tutorials/kolibri/` |

**Kiwix:** Die Play-Store-Version öffnet ZIMs über die Dateiauswahl; die APK-Version kann den Vault-Ordner durchsuchen.

**Web-Apps:** `offline-vault serve` in Termux starten und `http://localhost:8000` im Browser öffnen.
IT-Tools, Excalidraw und Drawnix bekommen eigene Ports (8001, 8002, ...), die das Portal auflistet.

---

### 💻 Lokaler Server (nur localhost)
- `offline-vault serve --static`: Portal und Web-Apps unter `http://localhost:8000`
- `offline-vault serve --kiwix`: Kiwix-Server unter `http://localhost:8000`
- `offline-vault serve --kolibri`: Kolibri unter `http://localhost:8080`
