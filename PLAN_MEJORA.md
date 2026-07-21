# Plan de Mejora — 01_MTG

> Generado por revisión completa 2026-07-14 (Merlin)

## Estado general

**Veredicto: aceptable.**

Proyecto maduro y sano: los 12 `.py` compilan (`py_compile` OK), los tests del parser pasan 14/14, no hay credenciales (Scryfall no requiere auth), `requirements.txt` con rangos acotados y `.gitignore` razonable. El diff sin commitear del 2026-07-10 (backoff en `translator.py` y `make_cards_old_border.py`) está bien hecho y verificado, pero lleva días en el working tree con riesgo real de regresión por Syncthing (ya pasó el 2026-06-10). El hallazgo nuevo más relevante: `data/artworks/` (5.702 JPGs, ~156 MB) sigue versionado en git pese a la decisión de 2026-07-01 de ignorarlo — el `.gitignore` solo evita archivos nuevos, nunca se hizo `git rm --cached`, y el `.git` pesa 548 MB. Además, `CLAUDE.md` no mencionaba `streamlit_app.py`, que es la UI principal del proyecto.

## Hallazgos

| Severidad | Categoría | Hallazgo | Archivo |
|-----------|-----------|----------|---------|
| **alta** (CONFIRMADO) | estructura | Trabajo real sin commitear desde 2026-07-10 (fix de backoff Scryfall) — riesgo de regresión Syncthing con precedente documentado (2026-06-10) | `translator.py`, `make_cards_old_border.py`, `PENDIENTES.md` |
| media | estructura | `data/artworks/` (5.702 JPGs, 156 MB) sigue versionado en git pese a la decisión de no versionarlo; `.git` pesa 548 MB. `git ls-files` lo confirma: el `.gitignore` solo cubre archivos nuevos | `.gitignore` / `data/artworks/` |
| media | docs | `CLAUDE.md` no mencionaba `streamlit_app.py` (UI principal, 3 pestañas) ni cómo lanzar la app | `CLAUDE.md` |
| baja | calidad | Duplicación de constantes de layout (`OUT_W/OUT_H`, `MANA_COL`, `COLOR_THEMES`, `rrect`, `place_art`, `fit_font`…) en 4 archivos — pendiente conocido de la auditoría 2026-07-01 | `make_cards_old_border.py`, `make_land_cards.py`, `generate_empty_frames.py`, `generate_land_frames.py` |
| baja | bug | `_RE_PLAIN` sigue aceptando líneas que no son cartas (p. ej. "4 copies recommended"), aunque ya está parcialmente mitigado (nombre ≥3 chars, count ≤99 en líneas 134-138) | `card_list_parser.py:33,134-138` |
| baja | estructura | Archivo `fabricar cartas y PDF` en la raíz es una lista de mazo Moxfield con nombre engañoso de script | `fabricar cartas y PDF` |
| baja | docs | Drift menor en ficha del cerebro y PENDIENTES.md: "artworks movidos a .gitignore" figura como hecho consumado, pendiente de pytest ya cerrado en la práctica, línea-count de `streamlit_app.py` desactualizado | `PENDIENTES.md` / ficha cerebro `01_MTG.md` |

_Ningún hallazgo fue refutado en la verificación adversarial._

## Mejoras ejecutadas hoy (2026-07-14)

- ✅ **Actualizar CLAUDE.md con la app Streamlit** — Añadido a "Comandos principales" el bloque de la interfaz web (`streamlit run streamlit_app.py`, puerto 8501, y `lanzar_mtg.bat` en Windows) y añadido `streamlit_app.py` al diagrama de arquitectura con sus imports reales (`ERAS`, `STAPLES`, `construir_mazo`, `a_moxfield`, `_cargar_db_local` de `deck_builder.py`; `translate_and_update_json` de `translator.py`) y sus 3 pestañas. Verificado contra el código real (`streamlit_app.py:7-8`, `lanzar_mtg.bat:10`).
- ✅ **Corregir el drift documental sobre `data/artworks/`** — Anotado en `PENDIENTES.md` (nuevo ítem en Incoherencias/riesgos) y en `📓 Notas MTG/README.md` que el destrackeo quedó a medias: los 4 JSONs sí salieron del índice, pero los 5.702 JPGs siguen trackeados (verificado con `git ls-files 'data/artworks/*' | wc -l` → 5702; `.git` = 548 MB). Comando exacto documentado para Daniel: `git rm -r --cached data/artworks/` + commit.
- ✅ **Matizar el pendiente de `_RE_PLAIN` en PENDIENTES.md** — El ítem ahora refleja que desde 2026-06-22 existe la validación `len(name) >= 3 and count <= 99` (`card_list_parser.py:134-138`, verificado en código) y que el fix restante es validar el nombre contra la DB local.

## Pendiente de Daniel

| Mejora | Motivo por el que no se hizo hoy |
|--------|----------------------------------|
| **Commitear ya el fix de backoff del 2026-07-10** — `git add translator.py make_cards_old_border.py PENDIENTES.md && git commit -m "fix: retry/backoff Scryfall en translator y renderer (reusa _request_with_backoff)" && git push`. El diff está revisado y es correcto (tests 14/14, py_compile OK, sin imports muertos). | El encargo prohíbe `git commit`/`push`. Riesgo activo de regresión Syncthing como la del 2026-06-10 — **prioridad 1 al volver**. |
| **Des-trackear `data/artworks/` del repo** — `git rm -r --cached data/artworks/` + commit (los JPGs locales NO se borran; `.gitignore` ya cubre los nuevos). Decidir además si reescribir historia (`git filter-repo` / BFG) para recuperar los ~548 MB del `.git`. | Modifica el índice git y requiere commit + posible force push al remoto `mtg-forge-lab`; reescribir historia es decisión suya. |
| **Refactor `card_layout.py`** — Extraer constantes y helpers duplicados en los 4 renderizadores; aprovechar para mover `_request_with_backoff` a un helper neutro (p. ej. `scryfall_utils.py`) y eliminar el acoplamiento translator→deck_builder del fix del 2026-07-10. | Refactor mediano que toca el renderizado de las +5.700 cartas; conviene verificar regenerando marcos y cartas de muestra. Decisión de alcance de Daniel. |
| **Renombrar `fabricar cartas y PDF`** — Es una lista de mazo Moxfield (60 cartas, descarte Old/Mid School) con nombre de script. Moverlo a `data/mazo_descarte_negro.txt` (quedaría gitignoreado) o eliminarlo si ya no se usa. | Implica mover/borrar un archivo trackeado — prohibido en esta fase; además es decisión suya si el mazo aún le sirve. |
| **Streaming del log en la pestaña Fabricar PDF** — Cambiar `subprocess.run` con `capture_output` por `subprocess.Popen` + lectura incremental en `st.empty()`. | Cambio funcional en la UI principal que conviene probar interactivamente con la app corriendo; prioridad baja definida por Daniel. |
| **Actualizar la ficha del cerebro `15_Merlin/cerebro/proyectos/01_MTG.md`** — dice `streamlit_app.py` "939 líneas" (hoy son 957) y da por hecho el destrackeo de artworks. | El encargo prohíbe tocar `15_Merlin/cerebro/`. |
