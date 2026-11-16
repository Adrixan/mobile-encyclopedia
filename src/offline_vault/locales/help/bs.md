# 📚 Vodič za Offline Knowledge Vault

### ⌨️ Tastatura
- **Razmak**: označi ili poništi označenu stavku
- **S**: preuzmi odabrane stavke koje nedostaju ili su zastarjele
- **P**: postavi ili promijeni putanju trezora (unaprijed: `~/offline_vault`, `/sdcard/Download/offline_vault`)
- **A**: odaberi sve vidljive resurse
- **C**: poništi odabir
- **F** / **/**: pređi na traku za pretragu i filter (`lang:bs`, `cat:wiki`, `tag:security`)
- **H** / **?**: otvori ovaj vodič, **Esc** ga zatvara
- **R**: osvježi katalog (najnovije verzije i veličine iz izvora)
- **Q**: izlaz

---

### 📂 Formati i folderi
Nazivi datoteka nemaju broj verzije, pa oznake ostaju ispravne nakon ažuriranja:
- **`.zim`** (sve kategorije): wikiji, DevDocs reference, pitanja i odgovori, kursevi, stripovi. Otvara se u Kiwixu.
- **`.epub`** (`admin/`, `dev/`): knjige. Otvara se u KOReaderu.
- **`.map`** (`maps/`): Mapsforge vektorske mape. Otvara se u Locus Map ili OruxMaps.
- **`tools/<id>/`**: gotove web aplikacije (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, periodni sistem, kalkulatori za sunce i mjesec).
- **`.z5` / `.z8`** (`fun/`): interaktivna fikcija. Igra se s `frotz` u Termuxu.
- **`apps/*.apk`**: Kiwix, KOReader, Trail Sense, Sky Map, Kolibri za instalaciju bez interneta.
- **`tutorials/kolibri/`**: Kolibri kanali (Sikana, CK-12, StoryWeaver). Potreban je `pip install kolibri`.

**Početni paket za telefon (oko 14 GB):** traži `tag:starter`, pritisni **A**, zatim **S**.

---

### 📱 Android
| Sadržaj | Aplikacija | Folder u trezoru |
| :--- | :--- | :--- |
| **`.zim`** | **Kiwix** (Play Store ili APK s download.kiwix.org) | bilo koja kategorija |
| **`.epub`** | **KOReader** (F-Droid) | `admin/`, `dev/` |
| **`.map`** | **Locus Map** / **OruxMaps** | `maps/` |
| **Web aplikacije** | Preglednik preko `offline-vault serve` u Termuxu | `tools/` |
| **`.z5` / `.z8`** | `pkg install frotz` u Termuxu | `fun/` |
| **`.apk`** | Upravitelj datoteka: instaliraj iz datoteke | `apps/` |
| **Kolibri** | Aplikacija **Kolibri**: uvoz iz foldera trezora | `tutorials/kolibri/` |

**Kiwix:** verzija iz Play Storea otvara ZIM datoteke preko birača datoteka; APK verzija može pretražiti folder trezora.

**Web aplikacije:** pokreni `offline-vault serve` u Termuxu i otvori `http://localhost:8000` u pregledniku.
IT-Tools, Excalidraw i Drawnix dobijaju vlastite portove (8001, 8002, ...), navedene na portalu.

---

### 💻 Lokalni server (samo localhost)
- `offline-vault serve --static`: portal i web aplikacije na `http://localhost:8000`
- `offline-vault serve --kiwix`: Kiwix server na `http://localhost:8000`
- `offline-vault serve --kolibri`: Kolibri na `http://localhost:8080`
