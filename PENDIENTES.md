# PENDIENTES — 01_MTG
_Auditoría 2026-06-18_

## 🐛 Bugs

- **[media]** `make_cards_old_border.py:401-409` y `make_cards_old_border.py:163-173` (`_folder_color`) — **Clasificación de color incompleta / incoherente entre frame y carpeta.** La detección solo captura `re.findall(r"\{([BWURGX])\}", ...)`, es decir maná de un único símbolo de color básico. Esto provoca dos fallos: (1) las cartas **multicolor** se guardan en la carpeta `output/cartas/multicolor/` (según `_folder_color`) pero se renderizan con el frame **`cafe`** (según `make_card_old`, que asigna `color="cafe"` para >1 color) → frame incorrecto. (2) El maná **híbrido/Phyrexiano** (`{W/U}`, `{2/W}`, `{B/P}`) y el genérico-con-color no se detectan, así que cartas claramente de color caen en `cafe` (incoloro). Fix: unificar la lógica en una sola función que use `colors`/`color_identity` de Scryfall (ya disponible en el JSON) en vez de parsear `mana_cost`, y crear un frame real para `multicolor` (hoy no existe `marco_multicolor_vacio.png`).

- **[media]** `streamlit_app.py:7` — **Import sin uso real / riesgo de error en arranque.** Se importa `buscar_cartas_db` desde `deck_builder` pero nunca se usa (código muerto). Más relevante: si `deck_builder.py` fallara al importar (p. ej. falta `requests`), toda la app cae en el `import` de la línea 7. Fix: eliminar `buscar_cartas_db` del import.

- **[baja]** `card_list_parser.py:33` (`_RE_PLAIN`) — **El parser "plain" puede tragarse líneas que empiezan por dígito y no son cartas.** Cualquier línea `^\d+\s+.+` se interpreta como carta (p. ej. un comentario "4 copies recommended" o "2 sideboard cards"). En el flujo actual es de bajo impacto porque las listas vienen de generadores propios, pero conviene anclar mejor o validar el nombre. Fix: validar contra DB local o exigir formato más estricto en modo plain.

- **[baja]** `make_cards_old_border.py:434` (`fetch_art_crop`) — **El arte siempre se re-descarga de Scryfall en cada generación**, incluso si ya existe `data/artworks/<nombre>.jpg` (que `download_artworks.py` precisamente genera). El docstring de `generate_all_cards.py` promete "usa data/artworks/<nombre>.jpg si existen (sin llamar a Scryfall)", pero `make_card_old` nunca lee esa carpeta: siempre va a la red. Fix: en `make_card_old`/`generate_card`, comprobar primero el artwork local antes de `fetch_art_crop`.

- **[baja]** `make_cards_old_border.py:577-579` — **Selección frágil de la sección del JSON Scryfall.** `entries_raw.get("mainboard") or entries_raw.get("columna") or next(iter(entries_raw.values()), [])`: si `mainboard` existe pero está vacío (`[]`), el `or` salta al siguiente y puede coger una sección equivocada (sideboard). Fix: comprobar presencia de clave con `in`, no truthiness.

## ⚠️ Incoherencias / riesgos

- **[media]** **Repositorio pesado: JSONs de datos versionados en git.** `git ls-files` muestra `data/cards_all_eras.json` (7,4 MB), `cards_mid_school.json` (6,2 MB), `cards_old_school.json` (1,3 MB) y `mtg_translations_es.json` (1,6 MB) trackeados. Son datos regenerables (`download_card_database.py`) o caché (traducciones). Mantenerlos en git infla el repo y genera diffs gigantes en cada actualización. A confirmar si es intencional; si no, moverlos a `.gitignore` y dejar instrucción de regeneración.

- **[media]** **`requirements.txt` sin versiones fijadas (`streamlit`, `Pillow`, `reportlab`, `requests`, `deep-translator`).** Sin pin, una actualización de Streamlit (API muy cambiante) o de Pillow puede romper la app sin avisar. Fix: fijar versiones (`pip freeze` del entorno que funciona) o al menos rangos mayores.

- **[media]** **`CLAUDE.md` desactualizado respecto al entorno real (Linux).** El README/CLAUDE.md documenta solo el flujo Windows (`.venv\Scripts\activate`, fuentes `C:/Windows/Fonts/...`). El entorno actual es Linux (PC Gamer Ubuntu). `make_cards_old_border.py` ya tiene fallback de fuentes Linux (bien), pero `make_land_cards.py:114-119` **solo** define rutas `C:/Windows/Fonts/...` sin fallback → en Linux cae a `ImageFont.load_default()` y las tierras saldrán con tipografía bitmap fea. Fix: portar el `_find_font(...)` de `make_cards_old_border.py` a `make_land_cards.py`; añadir notas Linux al README.

- **[baja]** **Dependencias no declaradas.** `test_card_list_parser.py` documenta uso con `pytest` pero `pytest` no está en `requirements.txt`. `card_list_parser.py:169` usa `tkinter` (clipboard) que no siempre viene instalado en Linux headless. No son bloqueantes (hay fallbacks), pero conviene documentarlos como extras.

- **[baja]** `download_card_database.py:38-43` — **`legalities` se conserva en cada carta** pero ninguna parte del proyecto lo usa. Es uno de los campos más voluminosos de Scryfall y multiplica el tamaño de los JSON. Fix: quitar `legalities` (y revisar si `keywords`/`color_identity` se usan) de `CAMPOS`.

- **[baja]** **`packages.txt` instala fuentes que no se usan como primera opción.** Declara `fonts-dejavu-core` y `fonts-liberation`; el código las busca, correcto. Coherente, solo verificar que el devcontainer (`pip3 install --user`) realmente las tenga disponibles tras `apt install`.

- **[baja]** `streamlit_app.py:266-267` — **Dependencia de CDNs externos** (`fonts.googleapis.com`, `cdn.jsdelivr.net/npm/mana-font@latest`). El `@latest` puede cambiar sin aviso y romper iconos; además sin red no hay iconos de maná. Fix: fijar versión de `mana-font` y/o servir local.

## ✨ Mejoras

- **[seguridad/robustez]** `streamlit_app.py:866-889` — La app ejecuta `subprocess.run([sys.executable, fabricador, "--input", ruta_fabricar])`. Está bien que use `sys.executable` y lista de args (no shell). Pero `ruta_fabricar` sale de un `selectbox` poblado por `os.listdir(DATA_DIR)`, así que es seguro. Mejora menor: añadir `timeout=` al `subprocess.run` para que un cuelgue de red no bloquee la UI indefinidamente.

- **[rendimiento]** `streamlit_app.py:628`, `:777` y `:920-924` — Las traducciones se leen de disco varias veces por render. `_cargar_traducciones()` ya usa `@st.cache_resource` (bien), pero el bloque de la consola (`:920`) abre y parsea el JSON otra vez sin caché. Fix: reutilizar `_cargar_traducciones()`.

- **[rendimiento]** `streamlit_app.py:631` — `_buscar_bilingue(..., max_results=500)` recorre toda la DB en Python por cada pulsación de tecla del buscador. Con ~5700 cartas es tolerable, pero para fluidez se podría indexar (precomputar minúsculas) o usar `@st.cache_data` sobre la query.

- **[robustez]** `translator.py` y `make_cards_old_border.py` — Las llamadas a Scryfall (`requests.get`) sin reintento/backoff (solo `download_card_database.py`/`deck_builder.py` lo tienen). Ante un 429 puntual, la traducción o el arte simplemente fallan en silencio. Fix: reusar `_request_with_backoff`.

- **[estructura]** Hay **duplicación masiva de constantes** (dimensiones `OUT_W/OUT_H/PAD/IX/...`, `MANA_COL`, `COLOR_THEMES`, `rrect`, `place_art`, `art_shadow`, `fit_font`) repetidas en `make_cards_old_border.py`, `make_land_cards.py`, `generate_empty_frames.py`, `generate_land_frames.py`. Fix: extraer a un módulo común `card_layout.py`.

- **[validación]** `make_cards_old_border.py:550` — Si `mtg_translations_es.json` no existe, el `open(...)` peta sin mensaje claro. Fix: comprobar existencia y dar instrucción (como hace `load_cards` en `generate_all_cards.py`).

- **[ux]** `streamlit_app.py` Tab 3 — El log del subproceso solo se muestra al terminar (no streaming). Para procesos de varios minutos, el usuario no ve progreso. Mejora opcional: streaming de `stdout`.

## ❓ Dudas / a confirmar con el usuario

1. **JSONs de datos en git (7 MB + 6 MB + …):** ¿es intencional versionarlos, o prefieres ignorarlos y regenerarlos con `download_card_database.py`? Afecta al tamaño del repo y a los diffs.
2. **Frame multicolor:** ¿quieres un `marco_multicolor_vacio.png` propio (oro/dual) o te vale que las multicolor usen el frame `cafe`? Hoy hay incoherencia entre carpeta (`multicolor`) y frame (`cafe`).
3. **Artworks locales:** ¿se llegó a usar `download_artworks.py`? El renderer nunca lee `data/artworks/`, así que ese paso del flujo documentado no surte efecto. ¿Lo quieres conectado para no depender de Scryfall en cada generación?
4. **Entorno objetivo:** ¿el flujo principal hoy es Linux (PC Gamer) o sigues fabricando en Windows (Legionario)? Define si merece la pena arreglar las fuentes de `make_land_cards.py` para Linux y actualizar el README.
5. **`maná híbrido/Phyrexiano` en Old/Mid School:** prácticamente no existe en esas eras (93-03), así que el bug de detección de color híbrido puede ser irrelevante en la práctica. ¿Confirmas que solo trabajas con esas eras?
