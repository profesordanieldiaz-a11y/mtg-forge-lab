import streamlit as st
import json
import os
import re
import subprocess
import sys
from deck_builder import ERAS, STAPLES, construir_mazo, a_moxfield, _cargar_db_local
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


_FRAME_TONES = {
    "W": ("#f4ecd2", "#a8966b", "#3a2e10"),
    "U": ("#3478b6", "#1e4f7f", "#eaf3ff"),
    "B": ("#22201d", "#0b0908", "#d8d4c8"),
    "R": ("#c44535", "#7c2419", "#fff1e8"),
    "G": ("#3f8a55", "#1f5232", "#eaf6e6"),
}
_RARITY_COLOR = {"common": "#555", "uncommon": "#9faab8", "rare": "#c9a961", "mythic": "#d96a26"}


def _oracle_to_html(text: str) -> str:
    if not text:
        return "<em style='opacity:0.45'>—</em>"
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    def _repl(m):
        s = m.group(1)
        css = _MANA_CSS.get(s.upper(), s.lower())
        return f'<i class="ms ms-{css} ms-cost" style="font-size:0.9em;vertical-align:middle;"></i>'
    text = re.sub(r"\{([^}]+)\}", _repl, text)
    return text.replace("\n", "<br>")


def _card_frame_html(card: dict, traducciones: dict) -> str:
    name     = card.get("name", "")
    t        = traducciones.get(name, {})
    nom_es   = t.get("name_es") or name
    tipo_es  = t.get("type_es") or card.get("type_line", "")
    text_es  = t.get("text_es") or card.get("oracle_text", "")
    cost     = card.get("mana_cost", "")
    colors   = card.get("colors", [])
    art_url  = card.get("art_crop", "")
    power    = card.get("power", "")
    toughness = card.get("toughness", "")
    rarity   = card.get("rarity", "common")
    set_code = card.get("set", "").upper()
    num      = card.get("collector_number", "")
    type_line = card.get("type_line", "")

    if "Land" in type_line:
        bg, border, fg = "#7a6a48", "#3d3422", "#f1ead0"
    elif "Artifact" in type_line:
        bg, border, fg = "#a0998a", "#534c3e", "#1a1612"
    elif len(colors) == 0:
        bg, border, fg = "#9c9587", "#5f574a", "#1a1612"
    elif len(colors) >= 2:
        bg, border, fg = "#d4b25a", "#7a5e1d", "#2a2010"
    else:
        bg, border, fg = _FRAME_TONES.get(colors[0], ("#9c9587", "#5f574a", "#1a1612"))

    rarity_col = _RARITY_COLOR.get(rarity, "#666")
    art_section = (
        f'<img src="{art_url}" style="width:100%;height:130px;object-fit:cover;display:block;">'
        if art_url else
        f'<div style="width:100%;height:130px;background:linear-gradient(135deg,{bg},{border});'
        f'display:flex;align-items:center;justify-content:center;color:{fg};font-size:10px;opacity:0.6;">{nom_es}</div>'
    )
    pt_html = (
        f'<div style="position:absolute;right:6px;bottom:6px;background:{bg};color:{fg};'
        f'padding:2px 8px;border-radius:3px;font-size:13px;font-weight:700;'
        f'box-shadow:inset 0 0 0 1px {border};font-family:Cormorant Garamond,serif;">'
        f'{power}/{toughness}</div>'
        if power and toughness else ""
    )
    cost_icons = mana_html(cost)
    text_html  = _oracle_to_html(text_es)

    return f"""
<div style="display:flex;justify-content:center;padding:4px 0 12px 0;">
<div style="width:230px;font-family:Inter,sans-serif;box-sizing:border-box;
  padding:10px;border-radius:11px;
  background:linear-gradient(180deg,{bg} 0%,{border} 100%);
  box-shadow:0 0 0 1px {border},0 10px 36px rgba(0,0,0,0.65),inset 0 1px 0 rgba(255,255,255,0.14);">
  <div style="border-radius:6px;background:#1a160f;padding:6px;display:flex;flex-direction:column;gap:4px;">
    <div style="display:flex;justify-content:space-between;align-items:center;
      background:linear-gradient(180deg,{bg} 0%,{border} 100%);
      padding:4px 8px;border-radius:4px;box-shadow:inset 0 0 0 1px {border};">
      <span style="font-family:'Cormorant Garamond',serif;font-weight:600;font-size:13px;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:130px;color:{fg};">{nom_es}</span>
      <span>{cost_icons}</span>
    </div>
    <div style="overflow:hidden;border-top:1px solid rgba(0,0,0,0.6);border-bottom:1px solid rgba(0,0,0,0.6);">
      {art_section}
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;
      background:linear-gradient(180deg,{bg} 0%,{border} 100%);
      padding:3px 8px;border-radius:4px;font-style:italic;font-size:10px;
      font-family:'Cormorant Garamond',serif;font-weight:600;
      box-shadow:inset 0 0 0 1px {border};color:{fg};">
      <span>{tipo_es}</span>
      <span style="color:{rarity_col};">◆</span>
    </div>
    <div style="background:rgba(244,236,210,0.92);color:#2a1e10;
      padding:6px 8px;border-radius:4px;font-size:10px;
      font-family:'Cormorant Garamond',serif;line-height:1.35;
      min-height:64px;position:relative;">
      {text_html}
      {pt_html}
    </div>
    <div style="font-size:8px;color:rgba(255,255,255,0.45);padding:0 4px;
      display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;">
      <span>{num} · {set_code}</span>
      <span style="opacity:0.6;">★ MTG LAB</span>
    </div>
  </div>
</div>
</div>
"""


# Session state — debe inicializarse antes de que cualquier pestaña se renderice
if "mi_mazo_manual" not in st.session_state:
    st.session_state["mi_mazo_manual"] = []
if "carta_preview" not in st.session_state:
    st.session_state["carta_preview"] = None

# Pre-computar para Tab 3 y la consola (se reutiliza en ambos sitios)
txts_disponibles = sorted([
    f for f in os.listdir(DATA_DIR) if f.endswith(".txt")
]) if os.path.isdir(DATA_DIR) else []


st.set_page_config(page_title="MTG Forge Lab", page_icon="🃏", layout="wide")

st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mana-font@0.14.0/css/mana.min.css">
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

                # Selectbox fuera del form → actualiza preview sin necesidad de submit
                nombre_es_elegido = st.selectbox(
                    f"Seleccionar carta ({total_txt}):",
                    list(nombres_filtrados.keys()) if nombres_filtrados else ["—"],
                    key="carta_seleccionada",
                )
                if nombre_es_elegido and nombre_es_elegido != "—" and nombres_filtrados:
                    _carta_en = nombres_filtrados.get(nombre_es_elegido)
                    _prev = next((c for c in resultados_filtrados if c.get("name") == _carta_en), None)
                    if _prev:
                        st.session_state["carta_preview"] = _prev

                with st.form("form_agregar_carta"):
                    col_cant, col_btn = st.columns([1, 2])
                    with col_cant:
                        cantidad = st.number_input("Cant.", min_value=1, max_value=4, value=1)
                    with col_btn:
                        st.markdown("<br>", unsafe_allow_html=True)
                        agregar = st.form_submit_button("➕ Agregar al mazo")
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
        # ── Vista de carta seleccionada ──────────────────────────
        _trad = _cargar_traducciones()
        if st.session_state.get("carta_preview"):
            st.html(_card_frame_html(st.session_state["carta_preview"], _trad))
        else:
            st.html("""
<div style="border:1px dashed oklch(0.32 0.015 65);border-radius:6px;
  padding:40px 20px;text-align:center;
  color:oklch(0.50 0.010 70);font-size:13px;font-family:Inter,sans-serif;">
  Selecciona una carta para ver su diseño
</div>""")
        st.divider()

        # ── Mazo manual ──────────────────────────────────────────
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
                    timeout=600,
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
    traducciones = _cargar_traducciones()
    if traducciones:
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


