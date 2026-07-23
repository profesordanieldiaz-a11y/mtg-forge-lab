#!/usr/bin/env python3
"""
generate_land_frames.py
Genera marcos vacios para las 5 tierras basicas en estilo old-border.
Guarda primero en pruebas/marcos_tierras/ para revision antes de mover a assets/marcos/
"""

from PIL import Image, ImageDraw
import os

# Layout, paleta y primitivas de dibujo compartidos (ver card_layout.py).
from card_layout import (
    OUT_W, OUT_H, PAD, IX, IXR,
    TT, TB, AT, AB, YT, YB, XT, XB, BT, BB,
    C, rrect,
)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PRUEBAS_DIR = os.path.join(SCRIPT_DIR, "pruebas", "marcos_tierras")

# Paletas para las 5 tierras basicas
# Colores inspirados en el viejo borde de MTG (Alpha/Beta/Revised)
# - tb_fill    : relleno de la caja de texto (pergamino con tinte del terreno)
# - tb_outline : borde de la caja de texto (color del terreno, saturado)
# - tl_fill    : relleno de la linea de tipo (oscuro, del color del terreno)
# - tl_outline : borde de la linea de tipo (medio, del color del terreno)

LAND_THEMES = {
    # Isla: azules oceanicos, superficie del agua al amanecer
    "isla": {
        "tb_fill":    (168, 210, 240),
        "tb_outline": ( 15,  58, 130),
        "tl_fill":    ( 22,  52, 112),
        "tl_outline": ( 42,  84, 148),
    },
    # Montaña: rojos volcanicos, piedra calcinada y lava
    "montana": {
        "tb_fill":    (230, 185, 148),
        "tb_outline": (118,  32,  10),
        "tl_fill":    ( 95,  26,  12),
        "tl_outline": (145,  50,  20),
    },
    # Bosque: verdes profundos, musgo y follaje denso
    "bosque": {
        "tb_fill":    (182, 208, 155),
        "tb_outline": ( 18,  58,  20),
        "tl_fill":    ( 22,  52,  18),
        "tl_outline": ( 44,  88,  32),
    },
    # Llanura: blancos calidos, marfil bañado por el sol
    "llanura": {
        "tb_fill":    (242, 236, 220),
        "tb_outline": (138, 126, 100),
        "tl_fill":    (122, 110,  88),
        "tl_outline": (162, 150, 126),
    },
    # Pantano: negros pantanosos, agua turbia y lodo
    "pantano": {
        "tb_fill":    (195, 180, 148),
        "tb_outline": ( 38,  30,  18),
        "tl_fill":    ( 26,  20,  12),
        "tl_outline": ( 60,  48,  28),
    },
    # Tierra Especial: plata/platino — acero frio con tinte azulado
    # Caja de texto: plata perlada clara
    # Barras:        acero oscuro azulado
    # Diamante:      acero medio — contraste sobre el fondo plateado
    "tierra_especial": {
        "tb_fill":    (215, 220, 230),
        "tb_outline": ( 88,  96, 118),
        "tl_fill":    ( 50,  54,  68),
        "tl_outline": ( 86,  94, 114),
    },
}

def make_land_frame(tierra: str, out_path: str) -> None:
    theme = LAND_THEMES[tierra]

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
    print(f"  [OK] marco_{tierra}_vacio.png")


if __name__ == "__main__":
    os.makedirs(PRUEBAS_DIR, exist_ok=True)
    print("[*] Generando marcos de tierras basicas en pruebas/marcos_tierras/...")
    for tierra in ["isla", "montana", "bosque", "llanura", "pantano"]:
        out = os.path.join(PRUEBAS_DIR, f"marco_{tierra}_vacio.png")
        make_land_frame(tierra, out)
    print(f"\n[OK] 5 marcos guardados en pruebas/marcos_tierras/")
    print("[!] Revisar antes de copiar a assets/marcos/")
