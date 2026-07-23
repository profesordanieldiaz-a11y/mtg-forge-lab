#!/usr/bin/env python3
"""
generate_empty_frames.py
Genera los marcos vacios para cada color en assets/marcos/
Usa el mismo estilo visual que make_cards_old_border.py
"""

from PIL import Image, ImageDraw
import os

# Layout, paleta y primitivas de dibujo compartidos con make_cards_old_border.py,
# make_land_cards.py y generate_land_frames.py (ver card_layout.py).
from card_layout import (
    OUT_W, OUT_H, PAD, IX, IXR,
    TT, TB, AT, AB, YT, YB, XT, XB, BT, BB,
    C, COLOR_THEMES, rrect,
)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
MARCOS_DIR  = os.path.join(SCRIPT_DIR, "assets", "marcos")

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
    for color in ["negro", "rojo", "azul", "verde", "blanco", "cafe", "multicolor"]:
        out = os.path.join(MARCOS_DIR, f"marco_{color}_vacio.png")
        make_empty_frame(color, out)
    print(f"\n[OK] 7 marcos guardados en assets/marcos/")
