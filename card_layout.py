#!/usr/bin/env python3
"""
card_layout.py — Definición única del layout visual de las cartas old-border.

Antes, estas dimensiones, paletas y helpers de dibujo vivían **copiados** en
`make_cards_old_border.py`, `make_land_cards.py`, `generate_empty_frames.py` y
`generate_land_frames.py`. Cualquier ajuste visual obligaba a tocar cuatro
archivos (y los marcos generados se desalineaban si te olvidabas de uno).

Todos los valores de aquí son el **superset exacto** de lo que tenía cada copia:
se verificó por AST que ninguna clave compartida difería entre archivos, así que
importar desde aquí no cambia ni un píxel del resultado.

No tiene efectos secundarios: solo constantes y funciones puras de dibujo.
"""

import os

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────
# DIMENSIONES  (500x700 px)
# ─────────────────────────────────────────────────────────────
OUT_W, OUT_H = 500, 700
PAD = 10
IX  = PAD + 8          # borde interior izquierdo = 18
IXR = OUT_W - PAD - 8  # borde interior derecho   = 482
IW  = IXR - IX         # ancho interior           = 464

# ── Zonas verticales ─────────────────────────────────────────
TT, TB = PAD + 8, 58              # título   (18–58,   40 px)
AT, AB = 60,      330             # arte     (60–330, 270 px)
YT, YB = 332,     370             # tipo     (332–370, 38 px)
XT, XB = 372,     624             # textbox  (372–624, 252 px)
BT, BB = 626,     OUT_H - PAD - 8 # pie      (626–682, 56 px)

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
# (los generadores de marcos vacíos solo usan los 4 primeros; `tb_text` les sobra
#  pero no les estorba)
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
    "multicolor": {
        "tb_fill":    (228, 210, 152),
        "tb_outline": ( 92,  68,  18),
        "tb_text":    ( 24,  18,   6),
        "tl_fill":    (140, 102,  24),
        "tl_outline": (196, 154,  56),
    },
}

# ─────────────────────────────────────────────────────────────
# COLORES DE MANA  →  (fondo, tinta)
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
    """Colores (fondo, tinta) de un símbolo de maná; gris neutro si no se conoce."""
    return MANA_COL.get(s, ((105, 105, 105), (255, 255, 255)))


# ─────────────────────────────────────────────────────────────
# FUENTES
#   Se prueban primero las de Windows (Legionario) y luego las de Linux
#   (PC Gamer): DejaVu → Liberation → FreeFont → Ubuntu.
# ─────────────────────────────────────────────────────────────
def find_font(*candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return candidates[0]


FONT_PATHS = {
    "bold": find_font(
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ),
    "reg": find_font(
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ),
    "srf": find_font(
        "C:/Windows/Fonts/georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ),
    "srfb": find_font(
        "C:/Windows/Fonts/georgiab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ),
    "srfi": find_font(
        "C:/Windows/Fonts/georgiai.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
    ),
}


def fnt(style, size):
    try:
        return ImageFont.truetype(FONT_PATHS.get(style, FONT_PATHS["reg"]), size)
    except Exception:
        return ImageFont.load_default()


def text_w(text, font) -> int:
    return int(font.getlength(text))


def fit_font(text, style, max_size, min_size, max_w):
    """Fuente más grande (entre max_size y min_size) con la que `text` cabe en `max_w`."""
    for sz in range(max_size, min_size - 1, -1):
        f = fnt(style, sz)
        if text_w(text, f) <= max_w:
            return f
    return fnt(style, min_size)


# ─────────────────────────────────────────────────────────────
# PRIMITIVAS DE DIBUJO
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
    img.paste(art, (x1 + (bw - nw) // 2, y1 + (bh - nh) // 2))


def art_shadow(img, x1, x2, y_bottom, height=50):
    """Degradado negro hacia arriba desde `y_bottom` (funde el arte con el marco)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(height):
        od.rectangle([x1, y_bottom - height + i, x2, y_bottom - height + i + 1],
                     fill=(0, 0, 0, int(180 * i / height)))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
