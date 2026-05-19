import streamlit as st
import json
import os
import re
import subprocess
import sys
from deck_builder import ERAS, STAPLES, construir_mazo, a_moxfield, buscar_cartas_db, _cargar_db_local
from translator import translate_and_update_json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "data")
PDF_DIR    = os.path.join(SCRIPT_DIR, "output", "PDF")


@st.cache_resource
def _cargar_traducciones():
    path = os.path.join(DATA_DIR, "mtg_translations_es.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_MANA_CSS = {
    "W": "w", "U": "u", "B": "b", "R": "r", "G": "g",
    "C": "c", "S": "s", "X": "x", "Y": "y", "Z": "z",
    "T": "tap", "Q": "untap", "E": "e", "P": "p",
    "W/U": "wu", "W/B": "wb", "U/B": "ub", "U/R": "ur",
    "B/R": "br", "B/G": "bg", "R/G": "rg", "R/W": "rw",
    "G/W": "gw", "G/U": "gu",
    "2/W": "2w", "2/U": "2u", "2/B": "2b", "2/R": "2r", "2/G": "2g",
}

def mana_html(cost: str) -> str:
    if not cost:
        return ""
    icons = []
    for s in re.findall(r"\{([^}]+)\}", cost):
        css = _MANA_CSS.get(s.upper(), s.lower())
        icons.append(f'<i class="ms ms-{css} ms-cost ms-shadow" title="{{{s}}}"></i>')
    return "".join(icons)


_ES_EN = {
    "vuela": "flying",     "volar": "flying",    "volador": "flying",  "vuelo": "flying",
    "arrolla": "trample",  "arrollar": "trample",
    "prisa": "haste",
    "vigilancia": "vigilance",
    "toque letal": "deathtouch",
    "vínculo vital": "lifelink",
    "indestructible": "indestructible",
    "alcance": "reach",
    "amenaza": "menace",
    "fulgor": "flash",
    "protección total": "hexproof",
    "velo": "shroud",
    "proliferar": "proliferate",
    "memoria": "flashback",
    "destruye": "destroy",   "destruir": "destroy",   "destrucción": "destroy",
    "destierra": "exile",    "desterrar": "exile",    "exilia": "exile",
    "descarta": "discard",   "descarte": "discard",   "descartar": "discard",
    "gira": "tap",           "girar": "tap",
    "endereza": "untap",     "enderezar": "untap",
    "sacrifica": "sacrifice","sacrificio": "sacrifice",
    "roba": "draw",          "robar": "draw",
    "busca": "search",       "buscar": "search",
    "baraja": "shuffle",     "mezcla": "shuffle",
    "regenera": "regenerate","regeneración": "regenerate",
    "previene": "prevent",   "prevenir": "prevent",
    "criatura": "creature",  "criaturas": "creature",
    "hechizo": "spell",      "hechizos": "spell",
    "tierra": "land",        "tierras": "land",
    "artefacto": "artifact", "artefactos": "artifact",
    "encantamiento": "enchantment",
    "cementerio": "graveyard",
    "biblioteca": "library",
    "campo de batalla": "battlefield",
    "maná": "mana",
    "contador": "counter",   "contadores": "counter",
    "objetivo": "target",
    "bloquea": "block",      "bloquear": "block",    "bloqueo": "block",
    "ataca": "attack",       "atacar": "attack",     "ataque": "attack",
    "daño": "damage",        "daños": "damage",
    "combate": "combat",
    "oponente": "opponent",
    "jugador": "player",
    "turno": "turn",
    "vida": "life",
}

def _buscar_bilingue(query: str, era_key: str, traducciones: dict, max_results: int = 30) -> list:
    """Busca cartas en inglés Y en español, expandiendo términos MTG al inglés equivalente."""
    db = _cargar_db_local(era_key)
    q = query.lower().strip()
    if not q:
        return []
    en_eq = _ES_EN.get(q)
    resultados = []
    vistos = set()
    for carta in db:
        name = carta.get("name", "")
        oracle = (carta.get("oracle_text") or "").lower()
        t = traducciones.get(name, {})
        if (q in name.lower() or
                q in carta.get("type_line", "").lower() or
                q in oracle or
                (en_eq and en_eq in oracle) or
                q in (t.get("name_es") or "").lower() or
                q in (t.get("type_es") or "").lower() or
                q in (t.get("text_es") or "").lower()):
            if name not in vistos:
                resultados.append(carta)
                vistos.add(name)
        if len(resultados) >= max_results:
            break
    return resultados


def _carta_coincide_color(c, cols):
    card_colors = c.get("colors", [])
    if "C" in cols and not card_colors:
        return True
    return any(col in card_colors for col in cols if col != "C")


def _mazo_manual_a_txt(cartas: list, nombre: str = "Mi Mazo Manual") -> str:
    hechizos = [c for c in cartas if not c.get("es_tierra")]
    tierras = [c for c in cartas if c.get("es_tierra")]
    total = sum(c["copias"] for c in cartas)
    lineas = [f"// Mazo: {nombre}", f"// Total: {total} cartas", ""]
    for c in hechizos:
        lineas.append(f"{c['copias']} {c['nombre']} ({c['set_code']}) {c['collector_number']}")
    if tierras:
        lineas.append("")
        for c in tierras:
            lineas.append(f"{c['copias']} {c['nombre']} ({c['set_code']}) {c['collector_number']}")
    return "\n".join(lineas)


# Session state — debe inicializarse antes de que cualquier pestaña se renderice
if "mi_mazo_manual" not in st.session_state:
    st.session_state["mi_mazo_manual"] = []

# Pre-computar para Tab 3 y la consola (se reutiliza en ambos sitios)
txts_disponibles = sorted([
    f for f in os.listdir(DATA_DIR) if f.endswith(".txt")
]) if os.path.isdir(DATA_DIR) else []


st.set_page_config(page_title="MTG Forge Lab", page_icon="🃏", layout="wide")

st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mana-font@latest/css/mana.min.css">
<style>
/* ══ MTG Lab Design System ══════════════════════════════════════ */
:root {
  --accent-h:   80;
  --bg:         oklch(0.16 0.012 60);
  --bg-1:       oklch(0.19 0.014 60);
  --bg-2:       oklch(0.22 0.014 60);
  --surface:    oklch(0.215 0.013 60);
  --surface-hi: oklch(0.255 0.014 60);
  --border:     oklch(0.32 0.015 65);
  --border-hi:  oklch(0.42 0.020 65);
  --text:       oklch(0.93 0.010 80);
  --text-dim:   oklch(0.66 0.012 70);
  --text-mute:  oklch(0.50 0.010 70);
  --accent:     oklch(0.75 0.13 80);
  --accent-hi:  oklch(0.82 0.14 80);
  --accent-glow:oklch(0.75 0.13 80 / 0.35);
  --danger:     oklch(0.66 0.18 25);
  --radius:     6px;
  --radius-lg:  10px;
}

/* ── Fondo y tipografía base ── */
.stApp, .main, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section {
  background:
    radial-gradient(1200px 600px at 20% -10%, oklch(0.22 0.02 75 / 0.40), transparent 60%),
    radial-gradient(900px 500px at 100% 110%, oklch(0.20 0.02 80 / 0.30), transparent 60%),
    var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', system-ui, sans-serif !important;
}
.block-container { padding-top: 2rem !important; }

/* ── Ocultar barra de herramientas de Streamlit ── */
[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--bg-1) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-dim) !important; }

/* ── Títulos ── */
h1 {
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 2.2rem !important; font-weight: 600 !important;
  letter-spacing: 0.02em !important; color: var(--text) !important;
  line-height: 1.1 !important;
}
h2, h3 {
  font-family: 'Cormorant Garamond', serif !important;
  font-weight: 600 !important; color: var(--text) !important;
}
h2 { font-size: 1.55rem !important; }
h3 { font-size: 1.2rem !important; }

/* ── Pestañas ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  gap: 0 !important; padding: 3px !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-dim) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important; font-weight: 500 !important;
  border-radius: 4px !important; border: none !important;
  padding: 8px 18px !important;
  transition: color 120ms !important;
}
.stTabs [aria-selected="true"] {
  background: var(--surface-hi) !important;
  color: var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Inputs y Selects ── */
.stTextInput input, .stSelectbox select,
.stNumberInput input, .stTextArea textarea {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: var(--radius) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  transition: border-color 120ms, box-shadow 120ms !important;
}
.stTextInput input:focus, .stSelectbox select:focus,
.stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-glow) !important;
}
.stTextInput label, .stSelectbox label,
.stNumberInput label, .stMultiSelect label,
.stRadio label > div:first-child, .stCheckbox label > div:first-child {
  color: var(--text-dim) !important;
  font-size: 11px !important; font-weight: 600 !important;
  letter-spacing: 0.08em !important; text-transform: uppercase !important;
}

/* ── Multiselect ── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
  background: oklch(0.24 0.05 80) !important;
  color: var(--accent) !important;
  border-radius: 999px !important;
}

/* ── Botones ── */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important; font-weight: 500 !important;
  transition: all 120ms !important;
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color: var(--border-hi) !important;
  color: var(--accent) !important;
}
.stButton button[kind="primary"],
.stDownloadButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
  background: var(--accent) !important;
  color: oklch(0.18 0.05 80) !important;
  border-color: var(--accent) !important;
  font-weight: 600 !important;
}
.stButton button[kind="primary"]:hover {
  background: var(--accent-hi) !important;
}

/* ── Métricas ── */
[data-testid="metric-container"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 14px !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 30px !important; font-weight: 600 !important;
  color: var(--accent) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 10px !important; font-weight: 600 !important;
  letter-spacing: 0.08em !important; text-transform: uppercase !important;
  color: var(--text-dim) !important;
}

/* ── Alertas ── */
.stAlert {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
}
[data-testid="stNotification"] { border-radius: var(--radius) !important; }

/* ── Expander ── */
.stExpander {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--surface) !important;
}
.stExpander summary {
  color: var(--text-dim) !important;
  font-size: 12px !important; letter-spacing: 0.04em !important;
}

/* ── Text area (lista Moxfield, log) ── */
.stTextArea textarea {
  background: oklch(0.13 0.01 60) !important;
  color: var(--text-dim) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important; line-height: 1.5 !important;
}

/* ── Code / caption ── */
code, .stCode { font-family: 'JetBrains Mono', monospace !important; color: var(--accent) !important; }
.stCaption { color: var(--text-mute) !important; font-size: 12px !important; }

/* ── Divisor ── */
hr { border-color: var(--border) !important; }

/* ── Tablas nativas de Streamlit (st.table) ── */
.stDataFrame, .stTable table {
  background: var(--bg) !important; color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
}

/* ── Icono de maná ── */
.ms { font-size: 1.25em; vertical-align: middle; }

/* ══ Tabla personalizada MTG ══════════════════════════════════ */
.mtg-tabla {
  width: 100%; border-collapse: separate; border-spacing: 0;
  font-size: 13px; font-family: 'Inter', sans-serif;
}
.mtg-tabla th {
  background: var(--bg-1) !important;
  color: var(--text-mute) !important;
  padding: 12px 10px; text-align: left;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 1;
  font-size: 10px !important; font-weight: 600 !important;
  letter-spacing: 0.1em !important; text-transform: uppercase !important;
}
.mtg-tabla td {
  padding: 8px 10px;
  border-bottom: 1px solid oklch(0.22 0.01 60);
  vertical-align: middle; color: var(--text-dim);
}
.mtg-tabla tr:hover td { background: var(--bg-1) !important; cursor: pointer; }
/* Nombre */
.mtg-tabla td:nth-child(2) {
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 15px !important; font-weight: 600 !important;
  color: var(--text) !important;
}
/* Tipo */
.mtg-tabla td:nth-child(4) {
  font-style: italic !important;
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 12px !important; color: var(--text-dim) !important;
}
/* Set */
.mtg-tabla td:nth-child(5) {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; color: var(--accent) !important;
}
.tabla-scroll {
  max-height: 450px; overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--bg);
}
.tabla-scroll::-webkit-scrollbar { width: 10px; height: 10px; }
.tabla-scroll::-webkit-scrollbar-track { background: transparent; }
.tabla-scroll::-webkit-scrollbar-thumb {
  background: oklch(0.28 0.01 60); border-radius: 5px;
  border: 2px solid var(--bg-1);
}
.tabla-scroll::-webkit-scrollbar-thumb:hover { background: oklch(0.36 0.015 60); }

/* ── Previsualización de carta ── */
.img-preview {
  border: 1px solid var(--border); border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.8); margin-bottom: 20px;
}

/* ── Scrollbars globales ── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: oklch(0.28 0.01 60); border-radius: 5px;
  border: 2px solid var(--bg-1);
}
::-webkit-scrollbar-thumb:hover { background: oklch(0.36 0.015 60); }

/* ── Ocultar sidebar ── */
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[kind="header"] { display: none !important; }
.block-container { max-width: 100% !important; }
</style>
""")

st.html("""
<div style="display:flex;align-items:center;gap:14px;padding:8px 0 20px 0;border-bottom:1px solid var(--border);margin-bottom:20px;">
  <div style="width:42px;height:42px;border-radius:10px;display:grid;place-items:center;
    background:radial-gradient(circle at 30% 30%,oklch(0.82 0.14 80),oklch(0.30 0.07 80) 70%);
    color:oklch(0.20 0.06 80);font-size:24px;font-weight:700;
    box-shadow:inset 0 1px 0 rgba(255,255,255,0.25),0 4px 14px oklch(0.75 0.13 80 / 0.35);">⌬</div>
  <div>
    <div style="font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:600;
      letter-spacing:0.02em;line-height:1;color:oklch(0.93 0.010 80);">MTG Lab</div>
    <div style="font-size:11px;color:oklch(0.66 0.012 70);letter-spacing:0.08em;
      text-transform:uppercase;margin-top:3px;">Forja Personal · GaiteroDade</div>
  </div>
</div>
""")

tabs = st.tabs(["🏗️ Constructor de Mazos", "🔍 Buscador & Mazo Manual", "🖨️ Fabricar PDF"])

# ════════════════════════════════════════════════════════════════
# PESTAÑA 1 — Constructor
# ════════════════════════════════════════════════════════════════
with tabs[0]:
    st.header("Construir Mazo Automático")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        arquetipo = st.selectbox("Arquetipo", list(STAPLES.keys()), format_func=lambda x: x.replace("_", " ").title())
    with col_opt2:
        era = st.selectbox("Era", list(ERAS.keys()), format_func=lambda x: ERAS[x]["nombre"])

    st.info(f"**Descripción:** {ERAS[era]['descripcion']}")

    if st.button("🚀 Generar Mazo"):
        with st.spinner("Construyendo mazo..."):
            mazo = construir_mazo(arquetipo, era)
            nombre_archivo = f"mazo_{arquetipo}_{era}.txt"
            ruta_txt = os.path.join(DATA_DIR, nombre_archivo)
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(a_moxfield(mazo))
            st.session_state["mazo_actual"] = mazo
            st.session_state["mazo_txt"]    = ruta_txt
            st.success(f"✅ Mazo guardado en `data/{nombre_archivo}`")

    if "mazo_actual" in st.session_state:
        mazo = st.session_state["mazo_actual"]
        col1, col2 = st.columns([1, 1])
        with col1:
            st.text_area("Lista Moxfield:", value=a_moxfield(mazo), height=350)
            st.metric("Total", mazo["total"])
            st.metric("Hechizos", mazo["total_hechizos"])
            st.metric("Tierras", mazo["total_tierras"])
        with col2:
            df_data = [
                {
                    "Cant":   c["copias"],
                    "Nombre": c["nombre"],
                    "Set":    c.get("set_code", ""),
                    "Tipo":   "Tierra" if c.get("es_tierra") else "Hechizo",
                    "CMC":    c.get("cmc", 0),
                }
                for c in mazo["cartas"]
            ]
            st.table(df_data)

# ════════════════════════════════════════════════════════════════
# PESTAÑA 2 — Buscador de Cartas / Mazo Manual
# ════════════════════════════════════════════════════════════════
with tabs[1]:
    st.header("Buscador de Cartas — Mazo Manual")

    col_buscar, col_mazo = st.columns([3, 2])

    with col_buscar:
        era_busq = st.selectbox(
            "Era de búsqueda",
            list(ERAS.keys()),
            key="era_busqueda",
            format_func=lambda x: ERAS[x]["nombre"],
        )
        query_busq = st.text_input("Buscar carta (nombre, tipo, efecto)...", key="query_busqueda")

        traducciones_db = _cargar_traducciones()

        if query_busq.strip():
            resultados = _buscar_bilingue(query_busq, era_busq, traducciones_db, max_results=500)
            if resultados:
                # Mapa nombre_es → nombre_en para todos los resultados
                nombres_es_map_total = {
                    (traducciones_db.get(c.get("name", ""), {}).get("name_es") or c.get("name", "")): c.get("name", "")
                    for c in resultados if c.get("name")
                }

                # Letras disponibles en los resultados actuales
                letras_disponibles = sorted(set(
                    (traducciones_db.get(c.get("name", ""), {}).get("name_es") or c.get("name", ""))[0].upper()
                    for c in resultados if c.get("name")
                ))

                # Filtro por letra (radio horizontal)
                letra_sel = st.radio(
                    "Filtrar por letra:",
                    ["✦"] + letras_disponibles,
                    horizontal=True,
                    key="letra_filtro",
                )
                letra_activa = None if letra_sel == "✦" else letra_sel

                # Aplicar filtro de letra
                if letra_activa:
                    nombres_filtrados_letra = {
                        es: en for es, en in nombres_es_map_total.items()
                        if es.upper().startswith(letra_activa)
                    }
                    resultados_letra = [
                        c for c in resultados if c.get("name") in set(nombres_filtrados_letra.values())
                    ]
                else:
                    nombres_filtrados_letra = nombres_es_map_total
                    resultados_letra = resultados

                # Filtro por color
                COLOR_LABELS = {"W": "⬜ Blanco", "U": "🔵 Azul", "B": "⚫ Negro", "R": "🔴 Rojo", "G": "🟢 Verde", "C": "◇ Incoloro"}
                colores_sel = st.multiselect(
                    "Filtrar por color:",
                    list(COLOR_LABELS.keys()),
                    format_func=lambda x: COLOR_LABELS[x],
                    key="color_filtro",
                )

                # Aplicar filtro de color
                if colores_sel:
                    resultados_filtrados = [c for c in resultados_letra if _carta_coincide_color(c, colores_sel)]
                    nombres_filtrados = {
                        es: en for es, en in nombres_filtrados_letra.items()
                        if en in {c.get("name") for c in resultados_filtrados}
                    }
                else:
                    resultados_filtrados = resultados_letra
                    nombres_filtrados = nombres_filtrados_letra

                total_txt = (
                    f"{len(resultados_filtrados)} cartas"
                    if not letra_activa and not colores_sel
                    else f"{len(resultados_filtrados)} de {len(resultados)} cartas"
                )

                # Formulario de selección SIEMPRE visible, encima de la tabla
                with st.form("form_agregar_carta"):
                    col_sel, col_cant, col_btn = st.columns([4, 1, 1])
                    with col_sel:
                        nombre_es_elegido = st.selectbox(
                            f"Seleccionar carta ({total_txt}):",
                            list(nombres_filtrados.keys()) if nombres_filtrados else ["—"],
                        )
                    with col_cant:
                        cantidad = st.number_input("Cant.", min_value=1, max_value=4, value=1)
                    with col_btn:
                        st.markdown("<br>", unsafe_allow_html=True)
                        agregar = st.form_submit_button("➕ Agregar")
                    if agregar and nombres_filtrados:
                        carta_elegida = nombres_filtrados.get(nombre_es_elegido)
                        card_data = next(
                            (c for c in resultados_filtrados if c.get("name") == carta_elegida), None
                        )
                        if card_data:
                            es_tierra = "Land" in card_data.get("type_line", "")
                            max_copias = 99 if es_tierra else 4
                            existente = next(
                                (e for e in st.session_state["mi_mazo_manual"] if e["nombre"] == carta_elegida),
                                None,
                            )
                            if existente:
                                existente["copias"] = min(existente["copias"] + cantidad, max_copias)
                            else:
                                st.session_state["mi_mazo_manual"].append({
                                    "nombre": carta_elegida,
                                    "copias": min(cantidad, max_copias),
                                    "set_code": card_data.get("set", "???").upper(),
                                    "collector_number": card_data.get("collector_number", "1"),
                                    "tipo": card_data.get("type_line", ""),
                                    "es_tierra": es_tierra,
                                    "mana_cost": card_data.get("mana_cost", ""),
                                    "cmc": card_data.get("cmc", 0),
                                })
                            st.rerun()

                # Tabla de resultados filtrados con scroll
                filas_html = []
                for c in resultados_filtrados:
                    name = c.get("name", "")
                    t = traducciones_db.get(name, {})
                    nombre_es = t.get("name_es") or name
                    tipo_es   = t.get("type_es") or c.get("type_line", "")
                    art_url   = c.get("art_crop", "")
                    img_html  = f'<img src="{art_url}" width="40" style="border-radius:4px">' if art_url else ""
                    coste_html  = mana_html(c.get("mana_cost", ""))
                    set_code    = c.get("set", "").upper()

                    filas_html.append(
                        f"<tr>"
                        f"<td>{img_html}</td>"
                        f"<td>{nombre_es}</td>"
                        f"<td style='white-space:nowrap'>{coste_html}</td>"
                        f"<td>{tipo_es}</td>"
                        f"<td>{set_code}</td>"
                        f"</tr>"
                    )
                if filas_html:
                    st.markdown(
                        "<div class='tabla-scroll'>"
                        "<table class='mtg-tabla'>"
                        "<thead><tr><th>Art</th><th>Nombre</th><th>Coste</th><th>Tipo</th><th>Set</th></tr></thead>"
                        f"<tbody>{''.join(filas_html)}</tbody>"
                        "</table>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info(f"No hay cartas con la letra '{letra_activa}' en esta búsqueda.")
            else:
                st.warning("No se encontraron cartas con ese texto.")

    with col_mazo:
        mazo_m = st.session_state["mi_mazo_manual"]
        total_m = sum(c["copias"] for c in mazo_m)
        hechizos_m = sum(c["copias"] for c in mazo_m if not c["es_tierra"])
        tierras_m = sum(c["copias"] for c in mazo_m if c["es_tierra"])

        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Total", total_m)
        cm2.metric("Hechizos", hechizos_m)
        cm3.metric("Tierras", tierras_m)

        if mazo_m:
            st.write("**Cartas en el mazo:**")
            for carta in list(mazo_m):
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.markdown(
                    f"{carta['copias']}× **{carta['nombre']}** {mana_html(carta['mana_cost'])}",
                    unsafe_allow_html=True,
                )
                if c2.button("−", key=f"menos_{carta['nombre']}"):
                    carta["copias"] -= 1
                    if carta["copias"] <= 0:
                        st.session_state["mi_mazo_manual"].remove(carta)
                    st.rerun()
                if c3.button("🗑", key=f"quitar_{carta['nombre']}"):
                    st.session_state["mi_mazo_manual"].remove(carta)
                    st.rerun()

            st.divider()
            nombre_manual = st.text_input("Nombre del archivo:", value="mi_mazo_manual", key="nombre_manual_input")
            txt_manual = _mazo_manual_a_txt(mazo_m, nombre_manual)

            col_dl, col_sv = st.columns(2)
            with col_dl:
                st.download_button(
                    "⬇️ Descargar .txt",
                    data=txt_manual,
                    file_name=f"{nombre_manual}.txt",
                    mime="text/plain",
                )
            with col_sv:
                if st.button("💾 Guardar en data/"):
                    ruta_manual = os.path.join(DATA_DIR, f"{nombre_manual}.txt")
                    with open(ruta_manual, "w", encoding="utf-8") as f:
                        f.write(txt_manual)
                    st.success(f"✅ `data/{nombre_manual}.txt`")
                    st.rerun()

            if st.button("🗑️ Limpiar mazo"):
                st.session_state["mi_mazo_manual"] = []
                st.rerun()
        else:
            st.info("El mazo está vacío. Busca y agrega cartas.")

# ════════════════════════════════════════════════════════════════
# PESTAÑA 3 — Fabricar Cartas + PDF
# ════════════════════════════════════════════════════════════════
with tabs[2]:
    st.header("Generación de Archivos")

    default_idx = 0
    if "mazo_txt" in st.session_state:
        nombre_reciente = os.path.basename(st.session_state["mazo_txt"])
        if nombre_reciente in txts_disponibles:
            default_idx = txts_disponibles.index(nombre_reciente)

    if txts_disponibles:
        archivo_elegido = st.selectbox(
            "Lista de cartas a fabricar:",
            txts_disponibles,
            index=default_idx,
        )
        ruta_fabricar = os.path.join(DATA_DIR, archivo_elegido)
        st.caption(f"📂 `data/{archivo_elegido}`")

        forzar = st.checkbox("🔄 Forzar regeneración (ignorar caché de imágenes)", value=False)

        if st.button("🃏 Fabricar Cartas y Generar PDF", type="primary"):
            fabricador = os.path.join(SCRIPT_DIR, "make_cards_old_border.py")
            cmd = [sys.executable, fabricador, "--input", ruta_fabricar]
            if forzar:
                cmd.append("--force")
            with st.spinner("Generando imágenes y PDF... (puede tardar varios minutos)"):
                resultado = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

            if resultado.returncode == 0:
                st.success("✅ ¡Cartas fabricadas correctamente!")
            else:
                st.error("❌ Hubo un error durante la fabricación.")

            with st.expander("📄 Log del proceso", expanded=(resultado.returncode != 0)):
                salida = resultado.stdout
                if resultado.stderr:
                    salida += "\n--- ERRORES ---\n" + resultado.stderr
                st.text(salida)

            nombre_base = os.path.splitext(archivo_elegido)[0].replace(" ", "_").replace("/", "-")
            nombre_pdf  = f"{nombre_base}_OldBorder_Imprimir.pdf"
            ruta_pdf    = os.path.join(PDF_DIR, nombre_pdf)
            if os.path.exists(ruta_pdf):
                st.success(f"📄 PDF listo: `output/PDF/{nombre_pdf}`")
                with open(ruta_pdf, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=f,
                        file_name=nombre_pdf,
                        mime="application/pdf",
                    )
            else:
                if os.path.isdir(PDF_DIR):
                    pdfs = sorted(
                        [p for p in os.listdir(PDF_DIR) if p.endswith(".pdf")],
                        key=lambda p: os.path.getmtime(os.path.join(PDF_DIR, p)),
                        reverse=True,
                    )
                    if pdfs:
                        st.info(f"PDF más reciente disponible: `output/PDF/{pdfs[0]}`")
    else:
        st.warning("No hay archivos `.txt` en la carpeta `data/`. Construye primero un mazo.")

st.divider()

# ════════════════════════════════════════════════════════════════
# PIE — Consola / Estado
# ════════════════════════════════════════════════════════════════
with st.expander("🛠️ Consola de Sistema / Estado"):
    json_path = os.path.join(DATA_DIR, "mtg_translations_es.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            traducciones = json.load(f)
        st.write(f"Cartas en base de datos local: **{len(traducciones)}**")

    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Archivos .txt en data/:**")
        for t in txts_disponibles:
            st.write(f"- `{t}`")
    with col_b:
        st.write("**PDFs generados:**")
        if os.path.isdir(PDF_DIR):
            for p in sorted(os.listdir(PDF_DIR)):
                if p.endswith(".pdf"):
                    st.write(f"- `{p}`")


