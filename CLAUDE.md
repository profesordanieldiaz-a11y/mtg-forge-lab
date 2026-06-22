# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos principales

```bash
# Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux (PC Gamer Ubuntu):
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# ── Flujo completo desde cero ──────────────────────────────────────
# 1. Descargar base de datos de cartas (~800 Old School + ~3000 Mid School)
python download_card_database.py

# 2. Generar todas las cartas en PNG (reanudable, omite las ya existentes)
python generate_all_cards.py
python generate_all_cards.py --era old          # solo Old School
python generate_all_cards.py --era mid          # solo Mid School
python generate_all_cards.py --batch 100        # procesar de a 100
python generate_all_cards.py --force            # regenerar aunque existan
python generate_all_cards.py --no-gt            # sin Google Translate

# 3. Generar tierras básicas (flujo separado)
python make_land_cards.py

# ── Desde un mazo específico (.txt en formato Moxfield/MTGO) ───────
python make_cards_old_border.py data/mazo_burn_mid_school.txt

# ── Utilidades ─────────────────────────────────────────────────────
python generate_empty_frames.py    # regenerar marcos vacíos en assets/marcos/
python generate_land_frames.py     # regenerar marcos de tierras
python download_artworks.py        # descargar art_crops en data/artworks/
python deck_builder.py             # modo interactivo para construir mazos
```

## Arquitectura

### Módulos y dependencias entre scripts

```
download_card_database.py   → genera data/cards_*.json  (Scryfall bulk, una sola vez)
       ↓
generate_all_cards.py       → orquestador principal (lee JSON, llama a make_card_old)
       ├── make_cards_old_border.py   → renderizador de carta individual (Pillow + ReportLab)
       └── translator.py             → Scryfall ES → Google Translate fallback → caché JSON

make_cards_old_border.py    → también puede usarse directamente con una lista .txt
       └── card_list_parser.py       → parsea formatos Moxfield / Arena / MTGO / plain text
```

### Dimensiones y zonas de la carta (500×700 px)

Todas las coordenadas están definidas como constantes en `make_cards_old_border.py`:

| Zona | Y inicio | Y fin | Descripción |
|------|---------|-------|-------------|
| Título | 18 | 58 | Nombre + coste de maná |
| Arte | 60 | 330 | `art_crop` de Scryfall |
| Tipo | 332 | 370 | Tipo de carta + símbolo de set |
| Textbox | 372 | 624 | Texto de reglas (autofit 23→11pt) |
| Pie | 626 | 682 | P/T para criaturas + info de colección |

### Traducción con caché

`translator.py` sigue esta prioridad: **Scryfall ES oficial → Google Translate → tabla fija de tipos**. Las traducciones se guardan en `data/mtg_translations_es.json` para evitar llamadas repetidas. `generate_all_cards.py` guarda el caché cada 25 cartas para que el proceso sea reanudable.

### Carpetas de salida

Las cartas generadas se guardan en `output/cartas/{color}/` donde `color` es: `azul`, `blanco`, `cafe`, `multicolor`, `negro`, `rojo`, `tierras`, `verde`. La función `_folder_color(mana_cost, is_land)` en `make_cards_old_border.py` determina a qué carpeta va cada carta.

### Marcos vacíos

Los marcos (`.png` en `assets/marcos/`) son la "plantilla" visual de cada color. Se generan con `generate_empty_frames.py` y `generate_land_frames.py`. Si un marco no existe al intentar generar una carta, el script falla con error claro. Los marcos deben regenerarse si se cambia el diseño visual.

### Límites de la API Scryfall

El script respeta el rate limit con `time.sleep(0.12)` entre llamadas. No hay autenticación requerida. `translator.py` reintenta hasta 3 veces con backoff exponencial ante 429; `generate_all_cards.py` se puede relanzar con `--batch` para continuar por partes.

### Notas Linux (PC Gamer Ubuntu)

- `make_cards_old_border.py` y `make_land_cards.py` tienen fallback de fuentes Linux (DejaVu / Liberation / FreeSans). No necesitan fuentes de Windows.
- Si no existe `data/mtg_translations_es.json`, `make_cards_old_border.py` muestra un error claro pidiendo ejecutar `generate_all_cards.py` primero.
- `tkinter` (usado por `load_card_list_clipboard`) puede faltar en entornos headless: `sudo apt install python3-tk`.
