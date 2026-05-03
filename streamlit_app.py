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
    """Convierte {W}{2}{U} en iconos HTML con Mana font."""
    if not cost:
        return ""
    icons = []
    for s in re.findall(r"\{([^}]+)\}", cost):
        css = _MANA_CSS.get(s.upper(), s.lower())
        icons.append(f'<i class="ms ms-{css} ms-cost ms-shadow" title="{{{s}}}"></i>')
    return "".join(icons)


def _buscar_bilingue(query: str, era_key: str, traducciones: dict, max_results: int = 30) -> list:
    """Busca cartas por nombre/tipo/texto en inglés Y en español."""
    db = _cargar_db_local(era_key)
    q = query.lower().strip()
    if not q:
        return []
    resultados = []
    vistos = set()
    for carta in db:
        name = carta.get("name", "")
        t = traducciones.get(name, {})
        if (q in name.lower() or
                q in carta.get("type_line", "").lower() or
                q in (carta.get("oracle_text") or "").lower() or
                q in (t.get("name_es") or "").lower() or
                q in (t.get("type_es") or "").lower() or
                q in (t.get("text_es") or "").lower()):
            if name not in vistos:
                resultados.append(carta)
                vistos.add(name)
        if len(resultados) >= max_results:
            break
    return resultados


st.set_page_config(page_title="MTG Forge Lab", page_icon="🃏", layout="wide")

st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mana-font@latest/css/mana.min.css">
<style>
.ms { font-size: 1.25em; vertical-align: middle; }
.mtg-tabla { width: 100%; border-collapse: collapse; font-size: 0.9em; }
.mtg-tabla th { background: #2c2c2c; color: #ddd; padding: 7px 10px; text-align: left; border-bottom: 2px solid #444; }
.mtg-tabla td { padding: 5px 10px; border-bottom: 1px solid #2a2a2a; vertical-align: middle; color: #ccc; }
.mtg-tabla tr:hover td { background: #1e1e1e; }
.mtg-tabla td:nth-child(5) { font-size: 0.82em; color: #888; }
</style>
""", unsafe_allow_html=True)

st.title("🃏 MTG Personal Lab")

# ════════════════════════════════════════════════════════════════
# SECCIÓN 1 — Construir Mazo
# ════════════════════════════════════════════════════════════════
st.sidebar.header("1️⃣ Construir Mazo")

arquetipo = st.sidebar.selectbox(
    "Arquetipo", list(STAPLES.keys()),
    format_func=lambda x: x.replace("_", " ").title()
)
era = st.sidebar.selectbox(
    "Era", list(ERAS.keys()),
    format_func=lambda x: ERAS[x]["nombre"]
)
st.sidebar.info(f"{ERAS[era]['descripcion']}")

if st.sidebar.button("🚀 Construir Mazo"):
    with st.spinner("Consultando Scryfall API..."):
        mazo = construir_mazo(arquetipo, era)
        nombre_archivo = f"mazo_{arquetipo}_{era}.txt"
        ruta_txt = os.path.join(DATA_DIR, nombre_archivo)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(a_moxfield(mazo))
        st.session_state["mazo_actual"] = mazo
        st.session_state["mazo_txt"]    = ruta_txt
        st.success(f"✅ Mazo guardado en `data/{nombre_archivo}`")

with st.expander("📋 Ver lista del mazo", expanded=False):
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
    else:
        st.info("Aún no has construido un mazo en esta sesión.")

st.divider()

# ════════════════════════════════════════════════════════════════
# SECCIÓN 2 — Buscador de Cartas / Mazo Manual
# ════════════════════════════════════════════════════════════════
st.subheader("🔍 Buscador de Cartas — Mazo Manual")

if "mi_mazo_manual" not in st.session_state:
    st.session_state["mi_mazo_manual"] = []


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
        resultados = _buscar_bilingue(query_busq, era_busq, traducciones_db, max_results=30)
        if resultados:
            st.caption(f"{len(resultados)} carta(s) encontrada(s)")
            filas_html = []
            for c in resultados:
                name = c.get("name", "")
                t = traducciones_db.get(name, {})
                nombre_es = t.get("name_es") or name
                tipo_es   = t.get("type_es") or c.get("type_line", "")
                texto_es  = t.get("text_es") or c.get("oracle_text") or ""
                texto_corto = (texto_es[:85] + "…") if len(texto_es) > 85 else texto_es
                coste_html  = mana_html(c.get("mana_cost", ""))
                set_code    = c.get("set", "").upper()
                filas_html.append(
                    f"<tr>"
                    f"<td>{nombre_es}</td>"
                    f"<td style='white-space:nowrap'>{coste_html}</td>"
                    f"<td>{tipo_es}</td>"
                    f"<td>{set_code}</td>"
                    f"<td>{texto_corto}</td>"
                    f"</tr>"
                )
            st.markdown(
                "<table class='mtg-tabla'>"
                "<thead><tr><th>Nombre</th><th>Coste</th><th>Tipo</th><th>Set</th><th>Texto</th></tr></thead>"
                f"<tbody>{''.join(filas_html)}</tbody>"
                "</table>",
                unsafe_allow_html=True,
            )

            with st.form("form_agregar_carta"):
                # Mostrar nombres en español en el dropdown
                nombres_es_map = {}
                for c in resultados:
                    en = c.get("name", "")
                    es = traducciones_db.get(en, {}).get("name_es") or en
                    nombres_es_map[es] = en
                nombre_es_elegido = st.selectbox("Seleccionar carta:", list(nombres_es_map.keys()))
                carta_elegida = nombres_es_map[nombre_es_elegido]
                cantidad = st.number_input("Cantidad", min_value=1, max_value=4, value=1)
                if st.form_submit_button("➕ Agregar al Mazo"):
                    card_data = next((c for c in resultados if c.get("name") == carta_elegida), None)
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

st.divider()

# ════════════════════════════════════════════════════════════════
# SECCIÓN 3 — Fabricar Cartas + PDF
# ════════════════════════════════════════════════════════════════
st.subheader("🖨️ Fabricar Cartas + PDF")

txts_disponibles = sorted([
    f for f in os.listdir(DATA_DIR) if f.endswith(".txt")
]) if os.path.isdir(DATA_DIR) else []

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

st.sidebar.markdown("---")
st.sidebar.caption("Creado con la Plantilla OGR para GaiteroDade")
