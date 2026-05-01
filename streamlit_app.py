import streamlit as st
import json
import os
import subprocess
import sys

try:
    from deck_builder import ERAS, STAPLES, construir_mazo, a_moxfield
except Exception as e:
    st.error(f"Error importando deck_builder: {e}")
    st.exception(e)
    st.stop()

try:
    from translator import translate_and_update_json
except Exception as e:
    st.error(f"Error importando translator: {e}")
    st.exception(e)
    st.stop()

try:
    from download_card_database import cargar_db, buscar_por_keyword
    _DB_DISPONIBLE = True
except Exception as e:
    _DB_DISPONIBLE = False
    _DB_ERROR = str(e)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "data")
PDF_DIR    = os.path.join(SCRIPT_DIR, "output", "PDF")

st.set_page_config(page_title="MTG Forge Lab", page_icon="🃏", layout="wide")
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
# SECCIÓN 2 — Fabricar Cartas + PDF  (siempre visible)
# ════════════════════════════════════════════════════════════════
st.subheader("🖨️ Fabricar Cartas + PDF")

# Buscar archivos .txt disponibles en data/
txts_disponibles = sorted([
    f for f in os.listdir(DATA_DIR) if f.endswith(".txt")
]) if os.path.isdir(DATA_DIR) else []

# Preseleccionar el del mazo recién construido si existe
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

    if st.button("🃏 Fabricar Cartas y Generar PDF", type="primary"):
        fabricador = os.path.join(SCRIPT_DIR, "make_cards_old_border.py")
        with st.spinner("Generando imágenes y PDF... (puede tardar varios minutos)"):
            resultado = subprocess.run(
                [sys.executable, fabricador, "--input", ruta_fabricar],
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

        # Buscar el PDF generado
        nombre_pdf = archivo_elegido.replace(".txt", "_OldBorder_Imprimir.pdf")
        ruta_pdf   = os.path.join(PDF_DIR, nombre_pdf)
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
            # Mostrar el PDF más reciente si no encuentra el exacto
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

st.divider()

# ════════════════════════════════════════════════════════════════
# SECCIÓN 3 — Base de Datos Local
# ════════════════════════════════════════════════════════════════
st.subheader("🗄️ Base de Datos Local de Cartas")

if not _DB_DISPONIBLE:
    st.error(f"Error cargando módulo de base de datos: {_DB_ERROR}")
else:
    path_all = os.path.join(DATA_DIR, "cards_all_eras.json")
    db_existe = os.path.exists(path_all)

    col_db1, col_db2 = st.columns([2, 1])
    with col_db1:
        if db_existe:
            db = cargar_db(path_all)
            st.success(f"Base local activa: **{len(db):,} cartas** (Old School + Mid School)")
        else:
            st.warning("No hay base local. Descárgala para búsquedas instantáneas sin depender de la API.")

    with col_db2:
        if st.button("⬇️ Descargar / Actualizar Base"):
            descargador = os.path.join(SCRIPT_DIR, "download_card_database.py")
            with st.spinner("Descargando de Scryfall... (1-2 minutos)"):
                resultado = subprocess.run(
                    [sys.executable, descargador],
                    input="s\n",
                    capture_output=True, text=True, encoding="utf-8", errors="replace"
                )
            if resultado.returncode == 0:
                st.success("✅ Base descargada correctamente.")
                st.rerun()
            else:
                st.error("❌ Error durante la descarga.")
                st.text(resultado.stderr)

    if db_existe:
        st.markdown("#### 🔍 Buscar cartas por palabra clave")
        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            keyword = st.text_input("Buscar en nombre, tipo o texto de reglas:", placeholder="ej: discard, flying, goblin, destroy...")
        with col_b2:
            era_filtro = st.selectbox("Era", ["Todas", "Old School", "Mid School"])

        if keyword:
            path_map = {
                "Todas":      path_all,
                "Old School": os.path.join(DATA_DIR, "cards_old_school.json"),
                "Mid School": os.path.join(DATA_DIR, "cards_mid_school.json"),
            }
            db_busqueda = cargar_db(path_map[era_filtro])
            resultados = buscar_por_keyword(keyword, db_busqueda)

            if resultados:
                st.write(f"**{len(resultados)} cartas encontradas:**")
                datos_tabla = [
                    {
                        "Nombre":  c.get("name", ""),
                        "Maná":    c.get("mana_cost", ""),
                        "Tipo":    c.get("type_line", ""),
                        "Set":     (c.get("set") or "").upper(),
                        "Rareza":  c.get("rarity", ""),
                        "Texto":   (c.get("oracle_text") or "")[:80] + ("..." if len(c.get("oracle_text") or "") > 80 else ""),
                    }
                    for c in resultados[:100]
                ]
                st.dataframe(datos_tabla, use_container_width=True)
                if len(resultados) > 100:
                    st.caption(f"Mostrando 100 de {len(resultados)} resultados. Refina la búsqueda.")
            else:
                st.info(f"No se encontraron cartas con '{keyword}' en {era_filtro}.")
