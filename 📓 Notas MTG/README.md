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

### Pendiente (necesita decisión de Daniel)

1. **JSONs en git** (`data/cards_*.json`, ~16 MB): ¿moverlos a `.gitignore` y regenerar con `download_card_database.py`?
2. **Frame multicolor**: ¿crear `marco_multicolor_vacio.png` propio (estilo oro) o mantener frame `cafe`?
3. **Artworks locales**: ¿conectar `download_artworks.py` con el renderer para no depender de Scryfall en cada generación?
4. **Entorno objetivo**: ¿Linux como principal? Define si vale la pena (ya está arreglado `make_land_cards.py`).
5. **Maná híbrido/Phyrexiano**: ¿irrelevante en eras 93-03? Si confirmas, el bug de color híbrido se puede cerrar.
