# 📓 Notas — MTG

Generador de cartas Magic: The Gathering (Python, Streamlit). Repo: `mtg-forge-lab`.

## Estado actual
Proyecto **maduro y funcional**. Flujo: descargar DB de Scryfall → generar cartas PNG → tierras/marcos. Bien documentado en `CLAUDE.md`.

## 🗓️ Sesión 2026-06-10 — Recuperación + tests
- **Recuperado de regresión de Syncthing**: `streamlit_app.py` había vuelto a la versión vieja de mayo (530 líneas); restaurado al código bueno de junio (939 líneas, incluye el rediseño visual). La versión vieja quedó en `git stash` por si acaso.
- **Tests nuevos**: `test_card_list_parser.py` — 14/14 pasan. Cubre los 4 formatos (Moxfield/Arena/MTGO/Plain), foil, secciones, comentarios y casos límite (`240p`, `1631★`). Correr: `python3 test_card_list_parser.py`.

## Pendientes
- Robustez ante error 429 de Scryfall: hoy el proceso se detiene; añadir reintento con backoff exponencial.
- Más tests para `_folder_color()` (asignación de color/carpeta).
- Verificar que `output/` no se haya colado al repo (debe estar en `.gitignore`).
