# Session Handoff (2026-10-23, Sprint 7)

## Trajectory
- Sprint 6 (morning): catalog v2, safe sync, Kolibri import (see git history `5b2efdf`).
- Sprint 7 (this session): Peter asked for replacements of the removed tools (Ptable, SunCalc, Excalidraw) runnable on the phone or servable from Termux, plus further personally relevant offline material at phone-realistic sizes.

## What changed
- New sources: `oci` (top layer of a Docker Hub image, layer digest = SHA-256; blob URL is a signed CDN redirect, so skip logic now compares SHA-256 before URL) and `fdroid` (suggested APK).
- New formats `apk`, `z5`, `z8` (signature checks); new category `apps`; `list`/`sync --tag`; resolver honours `GITHUB_TOKEN`/`GH_TOKEN`.
- Catalog 69 -> 134 items. Tools: Excalidraw, Drawnix (both `serve_root`), Future-Style Periodic Table, Astronomy Engine demos. Apps: Kiwix, KOReader, Trail Sense, Sky Map (F-Droid), Kolibri. Material: German Wikipedia/Wiktionary/Wikivoyage/Wikibooks/Klexikon/PhET DE, infosec SEs, OPSEC guides, OpenWrt, zimgit survival libraries, Low-Tech Magazine, outdoors/fitness/vegan Q&A, stoic and sci-fi EPUBs (Standard Ebooks), Jargon File, five freeware IF games, OpenAndroMaps Austria.
- Starter set: 60 items tagged `starter`, 14.35 GB.
- Generator (local only): `.scratch/gen_catalog.py` + `.scratch/catalog_spec.yaml` (top-level `starter:` key), run with `GH_TOKEN=$(gh auth token)`.

## Verification
- 102 tests green.
- Live sync of 19 new items (Docker layers, F-Droid, GitHub APKs, EPUBs, IF, ZIM, 1.2 GB OpenAndroMaps ZIP -> valid Mapsforge file); `.tmp` empty afterwards.
- Browser with all external hosts blocked: Excalidraw (local Excalifont), Drawnix, periodic table, sun/moon rise-set, IT-Tools work.
- Z-machine headers of all five games valid; no interpreter installed locally (frotz is a Termux package).

## Open decisions / next steps
- Excalidraw analytics script (online only) and Chinese default UIs (Drawnix, periodic table): document-only so far; patching upstream builds needs Peter's go.
- Not tested on a device: Trail Sense/Sky Map install from vault, Kiwix APK scanning `/sdcard/Download/offline_vault`.
- Backlog unchanged otherwise (`.agents/to-do.md`).
