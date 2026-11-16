# 📚 Guía del Offline Knowledge Vault

### ⌨️ Controles de teclado
- **Espacio**: marcar o desmarcar el elemento resaltado
- **S**: descargar los elementos seleccionados que faltan o están desactualizados
- **P**: elegir o cambiar la ruta del depósito (predefinidas: `~/offline_vault`, `/sdcard/Download/offline_vault`)
- **A**: seleccionar todos los recursos visibles
- **C**: borrar la selección
- **F** / **/**: ir a la barra de búsqueda y filtro (`lang:bs`, `cat:wiki`, `tag:security`)
- **H** / **?**: abrir esta guía, **Esc** la cierra
- **R**: actualizar el catálogo (versiones y tamaños más recientes desde las fuentes)
- **Q**: salir

---

### 📂 Formatos y carpetas
Los archivos no llevan versión en el nombre, así los marcadores sobreviven a las actualizaciones:
- **`.zim`** (todas las categorías): wikis, referencias de DevDocs, preguntas y respuestas, cursos, cómics. Se abren en Kiwix.
- **`.epub`** (`admin/`, `dev/`): libros. Se abren en KOReader.
- **`.map`** (`maps/`): mapas vectoriales Mapsforge. Se abren en Locus Map u OruxMaps.
- **`tools/<id>/`**: aplicaciones web ya compiladas (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, tabla periódica, calculadoras de sol y luna).
- **`.z5` / `.z8`** (`fun/`): ficción interactiva. Se juega con `frotz` en Termux.
- **`apps/*.apk`**: Kiwix, KOReader, Trail Sense, Sky Map, Kolibri para instalar sin conexión.
- **`tutorials/kolibri/`**: canales de Kolibri (Sikana, CK-12, StoryWeaver). Requiere `pip install kolibri`.

**Paquete inicial para el móvil (unos 14 GB):** busca `tag:starter`, pulsa **A** y luego **S**.

---

### 📱 Android
| Contenido | App | Carpeta del depósito |
| :--- | :--- | :--- |
| **`.zim`** | **Kiwix** (Play Store o APK de download.kiwix.org) | cualquier categoría |
| **`.epub`** | **KOReader** (F-Droid) | `admin/`, `dev/` |
| **`.map`** | **Locus Map** / **OruxMaps** | `maps/` |
| **Apps web** | Navegador con `offline-vault serve` en Termux | `tools/` |
| **`.z5` / `.z8`** | `pkg install frotz` en Termux | `fun/` |
| **`.apk`** | Gestor de archivos: instalar desde archivo | `apps/` |
| **Kolibri** | App **Kolibri**: importar desde la carpeta del depósito | `tutorials/kolibri/` |

**Kiwix:** la versión de Play Store abre los ZIM con el selector de archivos; la versión APK puede escanear la carpeta del depósito.

**Apps web:** ejecuta `offline-vault serve` en Termux y abre `http://localhost:8000` en el navegador.
IT-Tools, Excalidraw y Drawnix usan puertos propios (8001, 8002, ...), que aparecen en el portal.

---

### 💻 Servidor local (solo localhost)
- `offline-vault serve --static`: portal y apps web en `http://localhost:8000`
- `offline-vault serve --kiwix`: servidor Kiwix en `http://localhost:8000`
- `offline-vault serve --kolibri`: Kolibri en `http://localhost:8080`
