#!/usr/bin/env python3
"""
make_cards_old_border.py
Genera cartas MTG estilo Old Border en español a 500x700 px.

Frame: marco_negro_vacio.png (unico, 500x700)

Flujo por carta:
  1. Cargar marco_negro_vacio.png
  2. Descargar art_crop de Scryfall
  3. Pegar arte en zona de arte (mascara por brillo)
  4. Pegar frame encima
  5. Renderizar texto con autofit 23pt → 11pt (nombre, mana, tipo, reglas, P/T)
  6. Exportar PNG + PDF
"""

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
import requests, json, re, os, math, sys, argparse
from card_list_parser import load_card_list_file, load_card_list_clipboard
from translator import translate_and_update_json
from io import BytesIO

# ─────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR   = os.path.join(SCRIPT_DIR, "assets")
ICONOS_DIR   = os.path.join(ASSETS_DIR, "iconos")
MARCOS_DIR   = os.path.join(ASSETS_DIR, "marcos")
DATA_DIR     = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, "output")
PRUEBAS_DIR  = os.path.join(OUTPUT_DIR, "pruebas")
CARTAS_DIR   = os.path.join(OUTPUT_DIR, "cartas")

# ─────────────────────────────────────────────────────────────
# DIMENSIONES  (500x700 px)
# ─────────────────────────────────────────────────────────────
OUT_W, OUT_H = 500, 700
PAD = 10
IX  = PAD + 8        # borde interior izquierdo = 18
IXR = OUT_W - PAD - 8  # borde interior derecho  = 482
IW  = IXR - IX       # ancho interior            = 464

# ── Zonas verticales ─────────────────────────────────────────
TT, TB = PAD + 8, 58         # título      (18–58,  40 px)
AT, AB = 60,      330        # arte        (60–330, 270 px)
YT, YB = 332,     370        # tipo        (332–370, 38 px)
XT, XB = 372,     624        # textbox     (372–624, 252 px)
BT, BB = 626,     OUT_H - PAD - 8  # bottom (626–682, 56 px)

# ─────────────────────────────────────────────────────────────
# PALETA BASE
# ─────────────────────────────────────────────────────────────
C = {
    "border"  : (  5,  5,  8),
    "frame"   : ( 30, 25, 20),
    "gold"    : (155, 125, 62),
    "gold_l"  : (210, 175, 90),
    "t_name"  : (235, 212, 160),
    "t_info"  : (118, 108,  94),
}

# ─────────────────────────────────────────────────────────────
# TEMAS DE CUADRO DE TEXTO POR COLOR
#   tb_fill    → fondo pergamino del textbox
#   tb_outline → borde del textbox (color de la carta)
#   tb_text    → color del texto del cuerpo (oscuro sobre claro)
#   tl_fill    → fondo de la línea de tipo
#   tl_outline → borde de la línea de tipo
# ─────────────────────────────────────────────────────────────
COLOR_THEMES = {
    "negro":  {
        "tb_fill":    (210, 200, 173),
        "tb_outline": ( 50,  42,  30),
        "tb_text":    ( 24,  16,   8),
        "tl_fill":    ( 36,  28,  18),
        "tl_outline": ( 78,  62,  38),
    },
    "rojo":   {
        "tb_fill":    (224, 192, 162),
        "tb_outline": (108,  30,  14),
        "tb_text":    ( 28,  12,   6),
        "tl_fill":    ( 88,  28,  16),
        "tl_outline": (138,  52,  24),
    },
    "azul":   {
        "tb_fill":    (182, 214, 232),
        "tb_outline": ( 30,  70, 132),
        "tb_text":    (  8,  20,  54),
        "tl_fill":    ( 32,  68, 118),
        "tl_outline": ( 52,  98, 152),
    },
    "verde":  {
        "tb_fill":    (198, 212, 172),
        "tb_outline": ( 26,  60,  26),
        "tb_text":    ( 14,  24,   8),
        "tl_fill":    ( 30,  58,  26),
        "tl_outline": ( 52,  92,  38),
    },
    "blanco": {
        "tb_fill":    (234, 226, 208),
        "tb_outline": (126, 116,  92),
        "tb_text":    ( 28,  20,  12),
        "tl_fill":    (112, 102,  82),
        "tl_outline": (152, 142, 118),
    },
    "cafe":   {
        "tb_fill":    (210, 198, 172),
        "tb_outline": ( 88,  66,  38),
        "tb_text":    ( 24,  16,   8),
        "tl_fill":    ( 68,  50,  28),
        "tl_outline": (108,  80,  46),
    },
}

# ─────────────────────────────────────────────────────────────
# ICONOS DE MANÁ (uno por color)
# ─────────────────────────────────────────────────────────────
_ICON_CACHE = {}
_ICON_FILES = {
    "B": "Pantano icono.jpg",
    "W": "llanura Icono.jpg",
    "G": "Bosque Icono.jpg",
    "R": "Montaña Icono.png",
    "U": "Isla Icono.png",
}
_ICONS_DIR = ICONOS_DIR
# Iconos que requieren recoloreo: (color_anillo, color_fondo, color_simbolo)
_ICON_RECOLOR = {
    "U": ((30, 70, 140), (58, 108, 182), (215, 232, 252)),
    #      anillo azul    fondo azul medio  gota azul claro
}

def _get_icon(sym: str) -> Image.Image:
    if sym not in _ICON_CACHE:
        path = os.path.join(_ICONS_DIR, _ICON_FILES[sym])
        raw  = Image.open(path).convert("RGBA")
        bg   = Image.new("RGBA", raw.size, (255, 255, 255, 255))
        bg.paste(raw, mask=raw.split()[3])
        _ICON_CACHE[sym] = bg.convert("RGB")
    return _ICON_CACHE[sym]

# ─────────────────────────────────────────────────────────────
# COLORES DE MANA
# ─────────────────────────────────────────────────────────────
MANA_COL = {
    "B": ((20,15,20),    (210,190,215)),
    "W": ((245,235,200), (50,40,20)),
    "U": ((25,80,160),   (255,255,255)),
    "R": ((200,45,20),   (255,235,190)),
    "G": ((25,120,50),   (210,255,200)),
    "X": ((95,95,95),    (255,255,255)),
    "T": ((125,90,22),   (255,235,180)),
}
def mana_col(s):
    return MANA_COL.get(s, ((105,105,105), (255,255,255)))

_COLOR_FOLDER_MAP = {"B": "negro", "W": "blanco", "U": "azul", "R": "rojo", "G": "verde"}

def _folder_color(mana_str: str, is_land: bool = False) -> str:
    """Devuelve el nombre de la subcarpeta de output/cartas/ según el color."""
    if is_land:
        return "tierras"
    unique = [c for c in ["B", "W", "U", "R", "G"]
              if c in re.findall(r"\{([BWURGX])\}", mana_str)]
    if len(unique) == 1:
        return _COLOR_FOLDER_MAP[unique[0]]
    if len(unique) > 1:
        return "multicolor"
    return "cafe"

# ─────────────────────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────────────────────
def _find_font(*candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return candidates[0]

_FP = {
    "bold": _find_font(
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    "reg": _find_font(
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ),
    "srf": _find_font(
        "C:/Windows/Fonts/georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ),
    "srfb": _find_font(
        "C:/Windows/Fonts/georgiab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ),
    "srfi": _find_font(
        "C:/Windows/Fonts/georgiai.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ),
}

def fnt(style: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FP.get(style, _FP["reg"]), size)
    except Exception:
        return ImageFont.load_default()

def text_w(text: str, font) -> int:
    return int(font.getlength(text))

def fit_font(text: str, style: str, max_size: int, min_size: int, max_w: int):
    for sz in range(max_size, min_size - 1, -1):
        f = fnt(style, sz)
        if text_w(text, f) <= max_w:
            return f
    return fnt(style, min_size)

def total_lines_height(lines, lh_full, lh_blank):
    return sum(lh_blank if l is None else lh_full for l in lines)

def autofit_body(text: str, box_h: int, max_w: int, max_size: int = 30, min_size: int = 11):
    """Elige el tamaño mas grande que cabe en box_h, arrancando en 23pt."""
    for size in range(max_size, min_size - 1, -1):
        f   = fnt("srf", size)
        lh  = int(size * 1.45)
        lb  = max(5, int(size * 0.6))
        lns = wrap_runs(text, f, max_w)
        if total_lines_height(lns, lh, lb) <= box_h - 16:
            return f, lns, lh, lb
    f   = fnt("srf", min_size)
    lh  = int(min_size * 1.45)
    lb  = max(5, int(min_size * 0.6))
    return f, wrap_runs(text, f, max_w), lh, lb

# ─────────────────────────────────────────────────────────────
# DIBUJAR SIMBOLO DE MANA
# ─────────────────────────────────────────────────────────────
def draw_mana_sym(img: Image.Image, draw: ImageDraw.ImageDraw,
                  sym: str, cx: int, cy: int, r: int = 13) -> None:
    """Circulo de mana centrado en (cx,cy)."""
    bg, fg = mana_col(sym)
    if sym in _ICON_FILES:
        size = r * 2
        icon = _get_icon(sym)
        if sym in _ICON_RECOLOR:
            ring_col, bg_col, fg_col = _ICON_RECOLOR[sym]
            draw.ellipse([cx-r-1, cy-r-1, cx+r+1, cy+r+1], fill=ring_col)
            gray      = icon.convert("L")
            sym_mask  = gray.point(lambda p: 255 if p > 180 else 0)
            processed = Image.new("RGB", icon.size, bg_col)
            processed.paste(Image.new("RGB", icon.size, fg_col), mask=sym_mask)
            icon_r = processed.resize((size, size), Image.Resampling.LANCZOS)
        else:
            draw.ellipse([cx-r-1, cy-r-1, cx+r+1, cy+r+1], fill=(155, 125, 62))
            icon_r = icon.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size-1, size-1], fill=255)
        img.paste(icon_r, (cx - r, cy - r), mask=mask)
    else:
        draw.ellipse([cx-r-1, cy-r-1, cx+r+1, cy+r+1], fill=(155, 125, 62))
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg)
        f  = fnt("bold", max(8, r + 2))
        bb = draw.textbbox((0, 0), sym, font=f)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        draw.text((cx - tw//2, cy - th//2 - bb[1]), sym, fill=fg, font=f)

def draw_mana_cost(img: Image.Image, draw: ImageDraw.ImageDraw,
                   cost_str: str, right_x: int, mid_y: int, r: int = 13) -> None:
    symbols = re.findall(r"\{([^}]+)\}", cost_str)
    cx = right_x - r - 3
    for s in reversed(symbols):
        draw_mana_sym(img, draw, s, cx, mid_y, r)
        cx -= (r * 2 + 4)

# ─────────────────────────────────────────────────────────────
# TEXTO MIXTO  (texto + simbolos inline en textbox)
# ─────────────────────────────────────────────────────────────
SYM_R_INLINE = 9

def parse_runs(text: str) -> list:
    result = []
    for part in re.split(r"(\{[^}]+\})", text):
        if not part:
            continue
        m = re.match(r"\{([^}]+)\}", part)
        result.append(("s", m.group(1)) if m else ("t", part))
    return result

def wrap_runs(text: str, font, max_w: int) -> list:
    """Word-wrap con simbolos inline. None = separador de parrafo."""
    all_lines = []
    for para in text.split("\n"):
        runs = parse_runs(para)
        cur, cur_w = [], 0
        for kind, val in runs:
            if kind == "s":
                sw = SYM_R_INLINE * 2 + 4
                if cur_w + sw > max_w and cur:
                    all_lines.append(cur); cur, cur_w = [], 0
                cur.append(("s", val)); cur_w += sw
            else:
                for tok in re.split(r"(\s+)", val):
                    if not tok:
                        continue
                    tw = text_w(tok, font)
                    if cur_w + tw > max_w and cur:
                        all_lines.append(cur); cur, cur_w = [], 0
                    cur.append(("t", tok)); cur_w += tw
        all_lines.append(cur if cur else None)
    while all_lines and all_lines[-1] is None:
        all_lines.pop()
    return all_lines

def draw_text_line(img, draw, runs, x, y, font, text_color=(224, 214, 194)):
    cx     = x
    sym_cy = y + int(font.size * 0.62)
    for kind, val in runs:
        if kind == "t":
            draw.text((cx, y), val, fill=text_color, font=font)
            cx += text_w(val, font)
        else:
            draw_mana_sym(img, draw, val, cx + SYM_R_INLINE + 1, sym_cy, SYM_R_INLINE)
            cx += SYM_R_INLINE * 2 + 4

# ─────────────────────────────────────────────────────────────
# DESCARGA
# ─────────────────────────────────────────────────────────────
def fetch_art_crop(large_url: str):
    url = large_url.replace("/large/", "/art_crop/")
    try:
        r = requests.get(url, timeout=14)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"    [!] Arte: {e}")
    return None

def fetch_scryfall(name: str):
    url = f"https://api.scryfall.com/cards/named?exact={requests.utils.quote(name)}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    [!] Scryfall: {e}")
    return None

# ─────────────────────────────────────────────────────────────
# HELPERS DE DIBUJO
# ─────────────────────────────────────────────────────────────
def rrect(draw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, r, fill=fill, outline=outline, width=width)

def place_art(img, art, x1, y1, x2, y2):
    """Escala el arte para que entre completo (contain) sin recortar."""
    bw, bh = x2 - x1, y2 - y1
    aw, ah = art.size
    scale  = min(bw / aw, bh / ah)
    nw, nh = int(aw * scale), int(ah * scale)
    art    = art.resize((nw, nh), Image.Resampling.LANCZOS)
    ox     = x1 + (bw - nw) // 2
    oy     = y1 + (bh - nh) // 2
    img.paste(art, (ox, oy))

def art_shadow(img, x1, x2, y_bottom, height=50):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(height):
        alpha = int(180 * (i / height))
        od.rectangle([x1, y_bottom - height + i, x2, y_bottom - height + i + 1],
                     fill=(0, 0, 0, alpha))
    base = Image.alpha_composite(img.convert("RGBA"), overlay)
    img.paste(base.convert("RGB"))

# ─────────────────────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────
def make_card_old(name_orig: str, tr: dict, image_url: str,
                  power=None, toughness=None, out: str = "carta.png") -> Image.Image:
    is_creature = (power is not None and toughness is not None)
    mana_str    = tr.get("mana_cost", "")

    # ── Determinar color y cargar frame (Assets generados) ────
    colors_present = re.findall(r"\{([BWURGX])\}", mana_str)
    unique_colors  = [c for c in ["B","W","U","R","G"] if c in colors_present]
    COLOR_MAP = {"B": "negro", "W": "blanco", "U": "azul", "R": "rojo", "G": "verde"}
    if len(unique_colors) == 1:
        color = COLOR_MAP[unique_colors[0]]
    elif len(unique_colors) == 0:
        color = "cafe"   # incoloro/artefacto
    else:
        color = "cafe"   # multicolor → frame dorado/café por defecto

    frame_path = os.path.join(MARCOS_DIR, f"marco_{color}_vacio.png")
    if os.path.exists(frame_path):
        img = Image.open(frame_path).convert("RGB")
    else:
        img = Image.new("RGB", (OUT_W, OUT_H), C["border"])
        draw_f = ImageDraw.Draw(img)
        rrect(draw_f, [PAD, PAD, OUT_W-PAD, OUT_H-PAD], r=18, fill=C["frame"], outline=C["gold"], width=2)

    theme = COLOR_THEMES[color]
    draw  = ImageDraw.Draw(img)

    # ── Título ───────────────────────────────────────────────
    n_syms  = len(re.findall(r"\{[^}]+\}", mana_str))
    f_name  = fit_font(tr.get("name_es", name_orig), "bold", 20, 13,
                       IW - 20 - n_syms * 26)
    name_bb = draw.textbbox((0, 0), "A", font=f_name)
    name_y  = TT + (TB - TT) // 2 - (name_bb[3] - name_bb[1]) // 2
    draw.text((IX + 8, name_y), tr.get("name_es", name_orig),
              fill=C["t_name"], font=f_name)
    if mana_str:
        draw_mana_cost(img, draw, mana_str, IXR - 8, (TT + TB) // 2, r=11)

    # ── Arte ─────────────────────────────────────────────────
    art = fetch_art_crop(image_url) if image_url else None
    if art:
        place_art(img, art, IX + 1, AT + 1, IXR - 1, AB - 1)
        art_shadow(img, IX + 1, IXR - 1, AB - 1, height=50)
    else:
        draw.text((IX + IW // 2 - 30, (AT + AB) // 2 - 10), "[Sin arte]",
                  fill=C["t_info"], font=fnt("srfi", 14))
    draw = ImageDraw.Draw(img)

    # ── Línea de tipo ─────────────────────────────────────────
    rrect(draw, [IX, YT, IXR, YB], r=4,
          fill=theme["tl_fill"], outline=theme["tl_outline"], width=2)
    f_type = fit_font(tr.get("type_es", ""), "srfb", 16, 10, IW - 45)
    type_bb = draw.textbbox((0, 0), "A", font=f_type)
    type_y  = YT + (YB - YT) // 2 - (type_bb[3] - type_bb[1]) // 2
    draw.text((IX + 8, type_y), tr.get("type_es", ""), fill=theme["tb_fill"], font=f_type)
    sc_cx, sc_cy = IXR - 14, (YT + YB) // 2
    draw.polygon([
        (sc_cx,     sc_cy - 8),
        (sc_cx + 8, sc_cy),
        (sc_cx,     sc_cy + 8),
        (sc_cx - 8, sc_cy),
    ], fill=theme["tb_outline"], outline=theme["tl_outline"])

    # ── Cuadro de texto (pergamino, autofit 23pt → 11pt) ──────
    rrect(draw, [IX, XT, IXR, XB], r=5,
          fill=theme["tb_fill"], outline=theme["tb_outline"], width=3)
    text_es              = tr.get("text_es", "")
    f_body, lines, LH, LB = autofit_body(text_es, XB - XT, IW - 26)
    ty = XT + max(12, ((XB - XT) - total_lines_height(lines, LH, LB)) // 2)
    for line_runs in lines:
        if line_runs is None:
            ty += LB; continue
        if ty + LH > XB - 8:
            break
        draw_text_line(img, draw, line_runs, IX + 13, ty, f_body,
                       text_color=theme["tb_text"])
        ty += LH
    if ty + LH * 2 < XB - 12:
        draw.line([IX + 22, ty + 7, IXR - 22, ty + 7],
                  fill=theme["tb_outline"], width=1)

    # ── Barra inferior ───────────────────────────────────────
    draw.text((IX + 8, BT + (BB - BT) // 2 - 5),
              name_orig, fill=C["t_info"], font=fnt("reg", 9))

    # ── Power / Toughness ────────────────────────────────────
    if is_creature:
        pt_str = f"{power}/{toughness}"
        pw, ph = 72, 36
        px_pt  = IXR - pw - 4
        py_pt  = BT + (BB - BT) // 2 - ph // 2
        rrect(draw, [px_pt, py_pt, px_pt + pw, py_pt + ph], r=8,
              fill=theme["tl_fill"], outline=theme["tb_outline"], width=2)
        f_pt = fnt("bold", 20)
        bb   = draw.textbbox((0, 0), pt_str, font=f_pt)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((px_pt + pw // 2 - tw // 2, py_pt + ph // 2 - th // 2 - bb[1]),
                  pt_str, fill=theme["tb_fill"], font=f_pt)

    # ── Borde de corte exterior ──────────────────────────────
    rrect(draw, [0, 0, OUT_W - 1, OUT_H - 1], r=20, outline=C["border"], width=10)

    img.save(out, "PNG")
    print(f"  [OK] {os.path.basename(out)}")
    return img

# ─────────────────────────────────────────────────────────────
# GENERADOR DE PDF  (3x3 centrado en hoja carta)
# ─────────────────────────────────────────────────────────────
def make_pdf(png_paths: list, pdf_path: str) -> None:
    card_w = 63.5 * mm
    card_h = 88.9 * mm
    cols, rows = 3, 3
    per_page   = cols * rows
    page_w, page_h = letter
    margin_x = (page_w - cols * card_w) / 2
    margin_y = (page_h - rows * card_h) / 2

    pdf = rl_canvas.Canvas(pdf_path, pagesize=letter)
    for i, png in enumerate(png_paths):
        if i > 0 and i % per_page == 0:
            pdf.showPage()
        pos = i % per_page
        x   = margin_x + (pos % cols) * card_w
        y   = page_h - margin_y - (pos // cols + 1) * card_h
        pdf.drawImage(png, x, y, width=card_w, height=card_h)
    pdf.showPage()
    pdf.save()
    pages = math.ceil(len(png_paths) / per_page)
    print(f"  [OK] PDF: {len(png_paths)} cartas, {pages} paginas -> {pdf_path}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    # ── Argumentos ───────────────────────────────────────────
    ap = argparse.ArgumentParser(description="Genera cartas MTG estilo Old Border")
    ap.add_argument("--input", "-i", metavar="ARCHIVO",
                    help="Lista de cartas (.txt Moxfield, .json Scryfall) o 'clipboard'")
    ap.add_argument("--limit", "-n", type=int, metavar="N",
                    help="Limitar a las primeras N cartas (útil para pruebas)")
    ap.add_argument("--force", "-f", action="store_true",
                    help="Regenerar imágenes aunque ya existan en caché")
    # Compatibilidad: primer argumento posicional sin flag
    ap.add_argument("input_pos", nargs="?", metavar="ARCHIVO_POS", help=argparse.SUPPRESS)
    args = ap.parse_args()
    arg = args.input or args.input_pos

    os.makedirs(os.path.join(OUTPUT_DIR, "PDF"), exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    for sub in ("azul", "blanco", "cafe", "multicolor", "negro", "rojo", "tierras", "verde"):
        os.makedirs(os.path.join(CARTAS_DIR, sub), exist_ok=True)
    os.chdir(SCRIPT_DIR)

    print("[*] Cargando traducciones...")
    with open(os.path.join(DATA_DIR, "mtg_translations_es.json"), encoding="utf-8") as f:
        translations = json.load(f)

    print("[*] Cargando deck...")
    deck_name = "Mazo"
    entries_normalized = []

    if arg == "clipboard":
        print("  Leyendo desde portapapeles...")
        entries_normalized = load_card_list_clipboard()
        deck_name = "Portapapeles"

    elif arg and arg.lower().endswith(".txt"):
        path = arg if os.path.isabs(arg) else os.path.join(DATA_DIR, arg)
        print(f"  Leyendo lista de texto: {path}")
        entries_normalized = load_card_list_file(path)
        deck_name = os.path.splitext(os.path.basename(path))[0]

    else:
        json_path = arg if (arg and arg.lower().endswith(".json")) else os.path.join(DATA_DIR, "Cartas de todos los colores.json")
        if arg and arg.lower().endswith(".json") and not os.path.isabs(arg):
            json_path = os.path.join(DATA_DIR, arg)
        print(f"  Leyendo JSON Scryfall: {json_path}")
        with open(json_path, encoding="utf-8") as f:
            deck = json.load(f)
        deck_name = deck.get("name", "Mazo")
        entries_raw = deck.get("entries", {})
        scryfall_entries = (entries_raw.get("mainboard")
                            or entries_raw.get("columna")
                            or next(iter(entries_raw.values()), []))
        for entry in scryfall_entries:
            digest = entry.get("card_digest")
            if not digest:
                continue
            entries_normalized.append({
                "name":             digest["name"],
                "count":            entry.get("count", 1),
                "set_code":         digest.get("set", "").upper() or None,
                "collector_number": digest.get("collector_number"),
                "foil":             entry.get("finish", "") == "foil",
                "section":          entry.get("section", "mainboard"),
            })

    # ── Recopilar cartas únicas (solo mainboard) ──────────────
    unique_cards, order = {}, []
    for entry in entries_normalized:
        if entry["section"] not in ("mainboard", "columna"):
            continue
        name  = entry["name"]
        count = entry["count"]
        if name not in unique_cards:
            tr = translations.get(name, {
                "name_es": name, "type_es": "", "text_es": "", "mana_cost": ""
            })
            unique_cards[name] = {
                "tr": tr,
                "img_url": "",
                "power": None, "toughness": None,
                "count": 0,
                "type_line": "",
                "set_code": entry.get("set_code"),
                "is_land": False,
            }
            order.append(name)
        unique_cards[name]["count"] += count

    # ── Enriquecer con Scryfall ───────────────────────────────
    print(f"\n[*] {len(unique_cards)} cartas. Consultando Scryfall...")
    for name in order:
        data = fetch_scryfall(name)
        if data:
            type_line = data.get("type_line", "")
            unique_cards[name]["type_line"]   = type_line
            unique_cards[name]["is_land"]     = "Land" in type_line
            unique_cards[name]["oracle_text"] = data.get("oracle_text", "")
            img = data.get("image_uris", {}).get("large", "")
            if img:
                unique_cards[name]["img_url"] = img
            if "Creature" in type_line:
                unique_cards[name]["power"]     = data.get("power")
                unique_cards[name]["toughness"] = data.get("toughness")
            if not unique_cards[name]["tr"].get("mana_cost"):
                unique_cards[name]["tr"] = dict(unique_cards[name]["tr"],
                                                mana_cost=data.get("mana_cost", ""))
        c    = unique_cards[name]
        tipo = ("Tierra" if c["is_land"]
                else "Criatura" if c["power"]
                else "Hechizo/Instante/Artefacto")
        print(f"    {name} x{c['count']}  [{tipo}]")

    # ── Traducir cartas sin texto en español ──────────────────
    needs_translation = [
        {
            "name":        name,
            "oracle_text": unique_cards[name].get("oracle_text", ""),
            "type_line":   unique_cards[name]["type_line"],
            "mana_cost":   unique_cards[name]["tr"].get("mana_cost", ""),
        }
        for name in order
        if not unique_cards[name]["is_land"]
           and not unique_cards[name]["tr"].get("text_es")
    ]
    if needs_translation:
        print(f"\n[*] Traduciendo {len(needs_translation)} carta(s) sin traduccion...")
        translations = translate_and_update_json(
            needs_translation,
            os.path.join(DATA_DIR, "mtg_translations_es.json"),
        )
        for name in order:
            if name in translations:
                unique_cards[name]["tr"] = translations[name]

    # ── Separar tierras (sin marco disponible) ────────────────
    non_land_order = [n for n in order if not unique_cards[n]["is_land"]]
    land_order     = [n for n in order if unique_cards[n]["is_land"]]

    if land_order:
        print(f"\n[!] {len(land_order)} tierra(s) omitida(s) (sin marco disponible):")
        for n in land_order:
            print(f"    - {n} x{unique_cards[n]['count']}")

    if args.limit is not None:
        non_land_order = non_land_order[:args.limit]
        print(f"\n[LIMIT] Primeras {args.limit} cartas: {', '.join(non_land_order)}")

    order = non_land_order

    # ── Generar PNGs en output/cartas/{color}/ ────────────────
    print("\n[*] Generando imagenes Old Border...")
    png_cache = {}
    for idx, name in enumerate(order, 1):
        info   = unique_cards[name]
        fcolor = _folder_color(info["tr"].get("mana_cost", ""), info["is_land"])
        safe   = name.replace(" ", "_").replace("/", "-")
        out    = os.path.join(CARTAS_DIR, fcolor, f"{safe}.png")
        if os.path.exists(out) and not args.force:
            print(f"  [{idx}/{len(order)}] {name}  [cache] -> cartas/{fcolor}/")
        else:
            print(f"\n  [{idx}/{len(order)}] {name}  -> cartas/{fcolor}/")
            make_card_old(
                name_orig = name,
                tr        = info["tr"],
                image_url = info["img_url"],
                power     = info["power"],
                toughness = info["toughness"],
                out       = out,
            )
        png_cache[name] = out

    # ── Generar PDF con todas las copias ──────────────────────
    pdf_list = []
    for name in order:
        pdf_list.extend([png_cache[name]] * unique_cards[name]["count"])

    print(f"\n[*] Generando PDF ({len(pdf_list)} cartas)...")
    pdf_name = deck_name.replace(" ", "_").replace("/", "-")
    pdf_out  = os.path.join(OUTPUT_DIR, "PDF", f"{pdf_name}_OldBorder_Imprimir.pdf")
    make_pdf(pdf_list, pdf_out)

    print(f"\n[OK] Listo.")
    print(f"  PNGs  : {CARTAS_DIR}/{{color}}/")
    print(f"  PDF   : {pdf_out}")


if __name__ == "__main__":
    main()
