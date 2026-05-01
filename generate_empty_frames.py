#!/usr/bin/env python3
"""
generate_empty_frames.py
Genera los marcos vacios para cada color en assets/marcos/
Usa el mismo estilo visual que make_cards_old_border.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
MARCOS_DIR  = os.path.join(SCRIPT_DIR, "assets", "marcos")

OUT_W, OUT_H = 500, 700
PAD = 10
IX  = PAD + 8
IXR = OUT_W - PAD - 8
IW  = IXR - IX

TT, TB = PAD + 8, 58
AT, AB = 60,      330
YT, YB = 332,     370
XT, XB = 372,     624
BT, BB = 626,     OUT_H - PAD - 8

C = {
    "border": (  5,  5,  8),
    "frame" : ( 30, 25, 20),
    "gold"  : (155, 125, 62),
    "gold_l": (210, 175, 90),
}

COLOR_THEMES = {
    "negro":  {"tb_fill": (210,200,173), "tb_outline": ( 50, 42, 30), "tl_fill": ( 36, 28, 18), "tl_outline": ( 78, 62, 38)},
    "rojo":   {"tb_fill": (224,192,162), "tb_outline": (108, 30, 14), "tl_fill": ( 88, 28, 16), "tl_outline": (138, 52, 24)},
    "azul":   {"tb_fill": (182,214,232), "tb_outline": ( 30, 70,132), "tl_fill": ( 32, 68,118), "tl_outline": ( 52, 98,152)},
    "verde":  {"tb_fill": (198,212,172), "tb_outline": ( 26, 60, 26), "tl_fill": ( 30, 58, 26), "tl_outline": ( 52, 92, 38)},
    "blanco": {"tb_fill": (234,226,208), "tb_outline": (126,116, 92), "tl_fill": (112,102, 82), "tl_outline": (152,142,118)},
    "cafe":   {"tb_fill": (210,198,172), "tb_outline": ( 88, 66, 38), "tl_fill": ( 68, 50, 28), "tl_outline": (108, 80, 46)},
}

def rrect(draw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, r, fill=fill, outline=outline, width=width)

def make_empty_frame(color: str, out_path: str) -> None:
    theme = COLOR_THEMES[color]

    img  = Image.new("RGB", (OUT_W, OUT_H), C["border"])
    draw = ImageDraw.Draw(img)

    # Marco exterior
    rrect(draw, [PAD, PAD, OUT_W-PAD, OUT_H-PAD], r=18, fill=C["frame"], outline=C["gold"], width=2)

    # Zona titulo (vacia)
    rrect(draw, [IX, TT, IXR, TB], r=6, fill=theme["tl_fill"], outline=C["gold"], width=1)

    # Zona arte (vacia)
    draw.rectangle([IX, AT, IXR, AB], fill=C["border"])
    draw.rectangle([IX, AT, IXR, AB], outline=C["gold"], width=1)

    # Linea de tipo (vacia)
    rrect(draw, [IX, YT, IXR, YB], r=4, fill=theme["tl_fill"], outline=theme["tl_outline"], width=2)
    sc_cx, sc_cy = IXR - 14, (YT + YB) // 2
    draw.polygon([
        (sc_cx,     sc_cy - 8),
        (sc_cx + 8, sc_cy),
        (sc_cx,     sc_cy + 8),
        (sc_cx - 8, sc_cy),
    ], fill=theme["tb_outline"], outline=theme["tl_outline"])

    # Caja de texto (vacia)
    rrect(draw, [IX, XT, IXR, XB], r=5, fill=theme["tb_fill"], outline=theme["tb_outline"], width=3)

    # Barra inferior (vacia)
    draw.rectangle([IX, BT, IXR, BB], fill=C["frame"])

    # Borde de corte exterior
    rrect(draw, [0, 0, OUT_W-1, OUT_H-1], r=20, outline=C["border"], width=10)

    img.save(out_path, "PNG")
    print(f"  [OK] marco_{color}_vacio.png")


if __name__ == "__main__":
    os.makedirs(MARCOS_DIR, exist_ok=True)
    print("[*] Generando marcos vacios...")
    for color in ["negro", "rojo", "azul", "verde", "blanco", "cafe"]:
        out = os.path.join(MARCOS_DIR, f"marco_{color}_vacio.png")
        make_empty_frame(color, out)
    print(f"\n[OK] 6 marcos guardados en assets/marcos/")
