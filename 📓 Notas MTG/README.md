# 📓 Notas — MTG

Generador de cartas Magic: The Gathering (Python, Streamlit). Repo: `mtg-forge-lab`.

## Estado actual
Proyecto **maduro y funcional**. Flujo: descargar DB de Scryfall → generar cartas PNG → tierras/marcos. Bien documentado en `CLAUDE.md`.

## 🗓️ Sesión 2026-06-10 — Recuperación + tests
- **Recuperado de regresión de Syncthing**: `streamlit_app.py` había vuelto a la versión vieja de mayo (530 líneas); restaurado al código bueno de junio (939 líneas, incluye el rediseño visual). La versión vieja quedó en `git stash` por si acaso.
- **Tests nuevos**: `test_card_list_parser.py` — 14/14 pasan. Cubre los 4 formatos (Moxfield/Arena/MTGO/Plain), foil, secciones, comentarios y casos límite (`240p`, `1631★`). Correr: `python3 test_card_list_parser.py`.

## 🗓️ Sesión 2026-06-22 — Auditoría PENDIENTES.md (Merlin)

Revisión completa del proyecto por Merlin. 10 fixes aplicados en commit `5157fed`:

- `requirements.txt`: versiones fijadas con rangos (`streamlit>=1.31,<2.0`, etc.)
- `download_card_database.py`: eliminado campo `legalities` (no se usaba, reduce ~15% el tamaño de los JSON)
- `streamlit_app.py`: CDN mana-font `@latest` → `@0.14.0`; `timeout=600` en `subprocess.run`; consola usa `_cargar_traducciones()` en vez de abrir JSON directamente; import muerto `buscar_cartas_db` eliminado
- `translator.py`: backoff exponencial en `_fetch_scryfall_es` (3 reintentos ante 429)
- `make_cards_old_border.py`: error claro si falta `mtg_translations_es.json`; fix selección sección JSON (`in` vs truthiness)
- `make_land_cards.py`: fallback fuentes Linux portado (DejaVu / Liberation)
- `card_list_parser.py`: parser plain rechaza nombres <3 chars o count >99
- `CLAUDE.md`: comandos Linux añadidos + notas fuentes/tkinter

### Segunda ronda — decisiones ejecutadas (commits `0629f9e`, `cb6a6fa`)

- **JSONs fuera de git** — `data/cards_*.json`, `mtg_translations_es.json` y `data/artworks/` movidos a `.gitignore`. El repo bajó ~543k líneas. Regenerar con `download_card_database.py` / `download_artworks.py`.
  - ⚠️ **Corrección (2026-07-14, revisión Merlin):** el destrackeo quedó a medias. Los 4 JSONs sí salieron del índice, pero los **5.702 JPGs de `data/artworks/` siguen trackeados** (`.gitignore` solo evita archivos nuevos, nunca se corrió `git rm --cached`; `.git` pesa 548 MB). Pendiente de Daniel: `git rm -r --cached data/artworks/` + commit. Detalle en `PENDIENTES.md` y `PLAN_MEJORA.md`.
- **Frame multicolor dorado** — `marco_multicolor_vacio.png` generado (paleta oro/dual). Cartas con >1 color ya usan este frame en vez del `cafe` incorrecto.
- **Artworks locales conectados** — nueva función `load_art()` en `make_cards_old_border.py`: busca primero en `data/artworks/<nombre>.jpg`, solo va a Scryfall si no existe.
- **Entorno Linux confirmado** — `make_land_cards.py` ya tiene fallback de fuentes.
- **Bug maná híbrido cerrado** — irrelevante: proyecto solo trabaja con Old School (93–03) y Mid School (95–03).

**Estado final: PENDIENTES.md completamente resuelto. Sin items abiertos.**
