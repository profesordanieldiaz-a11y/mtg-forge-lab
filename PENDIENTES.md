# PENDIENTES — 01_MTG
_Auditoría 2026-06-18_

## 🐛 Bugs

- ~~**[media]** Clasificación de color multicolor / frame incorrecto~~ ✅ **RESUELTO 2026-06-22** — `marco_multicolor_vacio.png` creado (paleta oro/dual); cartas multicolor ya usan frame correcto. El maná híbrido/Phyrexiano es **irrelevante**: proyecto solo trabaja con Old School (93–03) y Mid School (95–03).

- ~~**[media]** `streamlit_app.py:7` — Import sin uso real `buscar_cartas_db`.~~ ✅ **RESUELTO 2026-06-22** — `buscar_cartas_db` ya no aparece en el import de `streamlit_app.py:7`. Verificado en código actual.

- **[baja]** `card_list_parser.py:33` (`_RE_PLAIN`) — **El parser "plain" puede tragarse líneas que empiezan por dígito y no son cartas.** Cualquier línea `^\d+\s+.+` se interpreta como carta (p. ej. un comentario "4 copies recommended" o "2 sideboard cards"). En el flujo actual es de bajo impacto porque las listas vienen de generadores propios, pero conviene anclar mejor o validar el nombre. Fix: validar contra DB local o exigir formato más estricto en modo plain.

- ~~**[baja]** `make_cards_old_border.py:434` (`fetch_art_crop`) — El arte siempre se re-descarga de Scryfall.~~ ✅ **RESUELTO 2026-06-22** — `load_art(card_name, image_url)` en línea 367 primero busca `data/artworks/<nombre>.jpg` local y solo llama a `fetch_art_crop` si no existe. `make_card_old` usa `load_art` en línea 456.

- ~~**[baja]** `make_cards_old_border.py:577-579` — Selección frágil de sección JSON con `or` (truthiness).~~ ✅ **RESUELTO 2026-06-22** — Líneas 602-607 ya usan `"mainboard" in entries_raw` (comprobación de clave) en lugar de truthiness. `mainboard` vacío `[]` ya no salta al siguiente.

## ⚠️ Incoherencias / riesgos

- ~~**[media]** **Repositorio pesado: JSONs de datos versionados en git** (`cards_all_eras.json` 7 MB, `cards_mid_school.json` 6 MB, `cards_old_school.json` 1,3 MB, `mtg_translations_es.json` 1,6 MB). Son datos regenerables/caché e inflan el repo.~~ ✅ **RESUELTO** (verificado 2026-07-01, drift) — **decisión: no versionarlos** (son regenerables). Ya están fuera de git: `git ls-files "*.json"` solo lista config (`.claude/settings.json`, `.devcontainer/devcontainer.json`); los 4 datos están en `.gitignore` (`data/cards_*.json`, `data/mtg_translations_es.json`) y `git check-ignore` los confirma ignorados. **Regeneración documentada** en CLAUDE.md → "Flujo completo desde cero": `python download_card_database.py` regenera `data/cards_*.json`; el caché de traducciones `mtg_translations_es.json` lo reconstruye `generate_all_cards.py` bajo demanda (Scryfall ES → Google Translate). Solo faltaba cerrar el drift aquí.

- ~~**[media]** **`requirements.txt` sin versiones fijadas (`streamlit`, `Pillow`, `reportlab`, `requests`, `deep-translator`).**~~ ✅ **RESUELTO** (verificado 2026-07-01, nocturno) — `requirements.txt` ya trae rangos mayores acotados: `streamlit>=1.31,<2.0`, `Pillow>=10.0,<13.0`, `reportlab>=3.6,<5.0`, `requests>=2.28`, `deep-translator>=1.11`. Una actualización mayor de Streamlit/Pillow ya no rompe la app en silencio.

- ~~**[media]** **`CLAUDE.md` desactualizado respecto al entorno real (Linux).**~~ ✅ **RESUELTO 2026-06-28** — `make_land_cards.py` ya tiene `_find_font(...)` con fallback Linux completo (DejaVu/Liberation/FreeSans/Ubuntu) en líneas 114-147. Verificado en código: ninguna ruta es solo-Windows. Pendiente cosmético (no bloquea): actualizar README/CLAUDE.md con instrucciones Linux.

- **[baja]** **Dependencias no declaradas.** `test_card_list_parser.py` documenta uso con `pytest` pero `pytest` no está en `requirements.txt`. `card_list_parser.py:169` usa `tkinter` (clipboard) que no siempre viene instalado en Linux headless. No son bloqueantes (hay fallbacks), pero conviene documentarlos como extras.

- ~~**[baja]** `download_card_database.py:38-43` — **`legalities` se conserva en cada carta** pero ninguna parte del proyecto lo usa. Es uno de los campos más voluminosos de Scryfall y multiplica el tamaño de los JSON. Fix: quitar `legalities` (y revisar si `keywords`/`color_identity` se usan) de `CAMPOS`.~~ ✅ **RESUELTO 2026-07-01** — verificado en código actual: `CAMPOS` (`download_card_database.py:38-43`) ya no incluye `legalities`; `grep -rn "legalities" --include="*.py"` no arroja usos en el proyecto. Sin cambios de código necesarios (drift del pendiente).

- **[baja]** **`packages.txt` instala fuentes que no se usan como primera opción.** Declara `fonts-dejavu-core` y `fonts-liberation`; el código las busca, correcto. Coherente, solo verificar que el devcontainer (`pip3 install --user`) realmente las tenga disponibles tras `apt install`.

- **[baja]** `streamlit_app.py:266-267` — **Dependencia de CDNs externos** (`fonts.googleapis.com`, `cdn.jsdelivr.net/npm/mana-font@latest`). El `@latest` puede cambiar sin aviso y romper iconos; además sin red no hay iconos de maná. Fix: fijar versión de `mana-font` y/o servir local.

## ✨ Mejoras

- ~~**[seguridad/robustez]** `streamlit_app.py:866-889` — La app ejecuta `subprocess.run([sys.executable, fabricador, "--input", ruta_fabricar])`. Está bien que use `sys.executable` y lista de args (no shell). Pero `ruta_fabricar` sale de un `selectbox` poblado por `os.listdir(DATA_DIR)`, así que es seguro. Mejora menor: añadir `timeout=` al `subprocess.run` para que un cuelgue de red no bloquee la UI indefinidamente.~~ ✅ **RESUELTO 2026-07-01** — verificado en código actual: `subprocess.run(...)` en `streamlit_app.py:878` ya trae `timeout=600`. Sin cambios de código necesarios (drift del pendiente).

- ~~**[rendimiento]** `streamlit_app.py:628`, `:777` y `:920-924` — Las traducciones se leen de disco varias veces por render. `_cargar_traducciones()` ya usa `@st.cache_resource` (bien), pero el bloque de la consola (`:920`) abre y parsea el JSON otra vez sin caché. Fix: reutilizar `_cargar_traducciones()`.~~ ✅ **RESUELTO 2026-07-01** — verificado en código actual: el bloque de la consola (`streamlit_app.py:922`) ya llama a `_cargar_traducciones()` en vez de abrir el JSON de nuevo. Sin cambios de código necesarios (drift del pendiente).

- **[rendimiento]** `streamlit_app.py:631` — `_buscar_bilingue(..., max_results=500)` recorre toda la DB en Python por cada pulsación de tecla del buscador. Con ~5700 cartas es tolerable, pero para fluidez se podría indexar (precomputar minúsculas) o usar `@st.cache_data` sobre la query.

- **[robustez]** `translator.py` y `make_cards_old_border.py` — Las llamadas a Scryfall (`requests.get`) sin reintento/backoff (solo `download_card_database.py`/`deck_builder.py` lo tienen). Ante un 429 puntual, la traducción o el arte simplemente fallan en silencio. Fix: reusar `_request_with_backoff`.

- **[estructura]** Hay **duplicación masiva de constantes** (dimensiones `OUT_W/OUT_H/PAD/IX/...`, `MANA_COL`, `COLOR_THEMES`, `rrect`, `place_art`, `art_shadow`, `fit_font`) repetidas en `make_cards_old_border.py`, `make_land_cards.py`, `generate_empty_frames.py`, `generate_land_frames.py`. Fix: extraer a un módulo común `card_layout.py`.

- ~~**[validación]** `make_cards_old_border.py:550` — Si `mtg_translations_es.json` no existe, el `open(...)` peta sin mensaje claro. Fix: comprobar existencia y dar instrucción (como hace `load_cards` en `generate_all_cards.py`).~~ ✅ **RESUELTO 2026-07-01** — verificado en código actual: `make_cards_old_border.py:572-576` ya comprueba `os.path.exists(trans_path)` y hace `sys.exit(...)` con instrucción de ejecutar `generate_all_cards.py` primero. Sin cambios de código necesarios (drift del pendiente).

- **[ux]** `streamlit_app.py` Tab 3 — El log del subproceso solo se muestra al terminar (no streaming). Para procesos de varios minutos, el usuario no ve progreso. Mejora opcional: streaming de `stdout`.

## ❓ Dudas / a confirmar con el usuario

1. **JSONs de datos en git (7 MB + 6 MB + …):** ¿es intencional versionarlos, o prefieres ignorarlos y regenerarlos con `download_card_database.py`? Afecta al tamaño del repo y a los diffs.
2. **Frame multicolor:** ¿quieres un `marco_multicolor_vacio.png` propio (oro/dual) o te vale que las multicolor usen el frame `cafe`? Hoy hay incoherencia entre carpeta (`multicolor`) y frame (`cafe`).
3. **Artworks locales:** ¿se llegó a usar `download_artworks.py`? El renderer nunca lee `data/artworks/`, así que ese paso del flujo documentado no surte efecto. ¿Lo quieres conectado para no depender de Scryfall en cada generación?
4. **Entorno objetivo:** ¿el flujo principal hoy es Linux (PC Gamer) o sigues fabricando en Windows (Legionario)? Define si merece la pena arreglar las fuentes de `make_land_cards.py` para Linux y actualizar el README.
5. **`maná híbrido/Phyrexiano` en Old/Mid School:** prácticamente no existe en esas eras (93-03), así que el bug de detección de color híbrido puede ser irrelevante en la práctica. ¿Confirmas que solo trabajas con esas eras?
