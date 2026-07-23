#!/usr/bin/env python3
"""
make_land_cards.py
Genera las 5 cartas de tierras basicas en estilo old-border:
  - Arte descargado de Scryfall (Alpha / LEA)
  - Nombre y tipo en español
  - Simbolo grande centrado en la caja de texto
  - Habilidad de toque con simbolos inline

Destino: pruebas/tierras/
"""

from PIL import Image, ImageDraw, ImageFont
import requests, os, re
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MARCOS_DIR = os.path.join(SCRIPT_DIR, "pruebas", "marcos_tierras")
ICONOS_DIR = os.path.join(SCRIPT_DIR, "assets", "iconos")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "pruebas", "tierras")

# Layout, paleta, fuentes y primitivas de dibujo compartidas con
# make_cards_old_border.py y los generadores de marcos (ver card_layout.py).
from card_layout import (
    OUT_W, OUT_H, PAD, IX, IXR, IW,
    TT, TB, AT, AB, YT, YB, XT, XB, BT, BB,
    C, MANA_COL, fnt, fit_font, rrect, place_art, art_shadow,
    text_w as tw,   # este archivo llama `tw` al medidor de ancho
)

LANDS = {
    "isla": {
        "name_es":   "Isla",
        "name_en":   "Island",
        "type_es":   "Tierra Básica — Isla",
        "icon_file": "Isla Icono.png",
        "tap_text":  "({T}: Agrega {U} a tu reserva de maná.)",
        "tb_fill":    (168, 210, 240),
        "tb_outline": ( 15,  58, 130),
        "tb_text":    (  8,  20,  54),
        "tl_fill":    ( 22,  52, 112),
        "tl_outline": ( 42,  84, 148),
    },
    "montana": {
        "name_es":   "Montaña",
        "name_en":   "Mountain",
        "type_es":   "Tierra Básica — Montaña",
        "icon_file": "Montaña Icono.png",
        "tap_text":  "({T}: Agrega {R} a tu reserva de maná.)",
        "tb_fill":    (230, 185, 148),
        "tb_outline": (118,  32,  10),
        "tb_text":    ( 28,  12,   6),
        "tl_fill":    ( 95,  26,  12),
        "tl_outline": (145,  50,  20),
    },
    "bosque": {
        "name_es":   "Bosque",
        "name_en":   "Forest",
        "type_es":   "Tierra Básica — Bosque",
        "icon_file": "Bosque Icono.jpg",
        "tap_text":  "({T}: Agrega {G} a tu reserva de maná.)",
        "tb_fill":    (182, 208, 155),
        "tb_outline": ( 18,  58,  20),
        "tb_text":    ( 14,  24,   8),
        "tl_fill":    ( 22,  52,  18),
        "tl_outline": ( 44,  88,  32),
    },
    "llanura": {
        "name_es":   "Llanura",
        "name_en":   "Plains",
        "type_es":   "Tierra Básica — Llanura",
        "icon_file": "llanura Icono.jpg",
        "tap_text":  "({T}: Agrega {W} a tu reserva de maná.)",
        "tb_fill":    (242, 236, 220),
        "tb_outline": (138, 126, 100),
        "tb_text":    ( 28,  20,  12),
        "tl_fill":    (122, 110,  88),
        "tl_outline": (162, 150, 126),
    },
    "pantano": {
        "name_es":   "Pantano",
        "name_en":   "Swamp",
        "type_es":   "Tierra Básica — Pantano",
        "icon_file": "Pantano icono.jpg",
        "tap_text":  "({T}: Agrega {B} a tu reserva de maná.)",
        "tb_fill":    (195, 180, 148),
        "tb_outline": ( 38,  30,  18),
        "tb_text":    ( 24,  16,   8),
        "tl_fill":    ( 26,  20,  12),
        "tl_outline": ( 60,  48,  28),
    },
}


# ── Arte ──────────────────────────────────────────────────────
def fetch_land_art(name_en: str, set_code: str = "lea"):
    try:
        r = requests.get(
            f"https://api.scryfall.com/cards/named?exact={name_en}&set={set_code}",
            timeout=10)
        if r.status_code == 200:
            url = r.json().get("image_uris", {}).get("art_crop", "")
            if url:
                r2 = requests.get(url, timeout=15)
                if r2.status_code == 200:
                    return Image.open(BytesIO(r2.content)).convert("RGB")
    except Exception as e:
        print(f"    [!] Arte: {e}")
    return None


# ── Símbolo inline pequeño ────────────────────────────────────
SYM_R = 11

def draw_sym(draw, sym, cx, cy, r=SYM_R):
    bg, fg = MANA_COL.get(sym, ((105, 105, 105), (255, 255, 255)))
    draw.ellipse([cx-r-1, cy-r-1, cx+r+1, cy+r+1], fill=(155, 125, 62))
    draw.ellipse([cx-r,   cy-r,   cx+r,   cy+r  ], fill=bg)
    f  = fnt("bold", max(8, r + 2))
    bb = draw.textbbox((0, 0), sym, font=f)
    draw.text((cx - (bb[2]-bb[0])//2, cy - (bb[3]-bb[1])//2 - bb[1]),
              sym, fill=fg, font=f)

# ── Línea de texto mixto centrada horizontalmente ─────────────
def draw_mixed_centered(draw, text, y, font, text_col):
    parts = re.split(r"(\{[^}]+\})", text)

    total_w = sum(
        (SYM_R * 2 + 4) if (p and p.startswith("{")) else tw(p, font)
        for p in parts if p
    )

    cx     = (OUT_W - total_w) // 2
    sym_cy = y + int(font.size * 0.62)

    for p in parts:
        if not p:
            continue
        if p.startswith("{"):
            draw_sym(draw, p[1:-1], cx + SYM_R + 1, sym_cy)
            cx += SYM_R * 2 + 4
        else:
            draw.text((cx, y), p, fill=text_col, font=font)
            cx += tw(p, font)

# ── Ícono grande con máscara circular ────────────────────────
ICON_SIZE = 110

def draw_large_icon(img, icon_path, center_x, top_y, size=ICON_SIZE):
    raw  = Image.open(icon_path).convert("RGBA")
    icon = raw.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    img.paste(icon, (center_x - size // 2, top_y), mask=mask)

# ── Generador principal ───────────────────────────────────────
def make_land_card(tierra: str, out_path: str):
    d = LANDS[tierra]

    # Marco base
    img  = Image.open(os.path.join(MARCOS_DIR, f"marco_{tierra}_vacio.png")).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Arte de Scryfall Alpha
    print(f"  Descargando arte de {d['name_en']}...")
    art = fetch_land_art(d["name_en"])
    if art:
        place_art(img, art, IX + 1, AT + 1, IXR - 1, AB - 1)
        art_shadow(img, IX + 1, IXR - 1, AB - 1)
        draw = ImageDraw.Draw(img)
    else:
        print(f"    [!] Sin arte para {d['name_en']}")

    # Título
    f_name = fit_font(d["name_es"], "bold", 22, 14, IW - 20)
    bb     = draw.textbbox((0, 0), "A", font=f_name)
    name_y = TT + (TB - TT) // 2 - (bb[3] - bb[1]) // 2
    draw.text((IX + 8, name_y), d["name_es"], fill=C["t_name"], font=f_name)

    # Línea de tipo
    rrect(draw, [IX, YT, IXR, YB], r=4, fill=d["tl_fill"], outline=d["tl_outline"], width=2)
    f_type = fit_font(d["type_es"], "srfb", 22, 14, IW - 45)
    bb     = draw.textbbox((0, 0), "A", font=f_type)
    type_y = YT + (YB - YT) // 2 - (bb[3] - bb[1]) // 2
    draw.text((IX + 8, type_y), d["type_es"], fill=d["tb_fill"], font=f_type)
    sc_cx, sc_cy = IXR - 14, (YT + YB) // 2
    draw.polygon([
        (sc_cx,     sc_cy - 8), (sc_cx + 8, sc_cy),
        (sc_cx,     sc_cy + 8), (sc_cx - 8, sc_cy),
    ], fill=d["tb_outline"], outline=d["tl_outline"])

    # Caja de texto
    rrect(draw, [IX, XT, IXR, XB], r=5, fill=d["tb_fill"], outline=d["tb_outline"], width=3)

    # Layout vertical centrado: ícono + gap + texto de toque
    f_tap     = fnt("srf", 19)
    tap_line_h = int(19 * 1.3)
    content_h  = ICON_SIZE + 14 + tap_line_h
    icon_top_y = XT + (XB - XT - content_h) // 2

    # Ícono grande (símbolo del tipo de tierra)
    draw_large_icon(img, os.path.join(ICONOS_DIR, d["icon_file"]),
                    OUT_W // 2, icon_top_y)
    draw = ImageDraw.Draw(img)

    # Texto de habilidad de toque centrado bajo el ícono
    tap_y = icon_top_y + ICON_SIZE + 14
    draw_mixed_centered(draw, d["tap_text"], tap_y, f_tap, d["tb_text"])

    # Barra inferior — nombre en inglés
    draw.text((IX + 8, BT + (BB - BT) // 2 - 5),
              d["name_en"], fill=C["t_info"], font=fnt("reg", 12))

    # Borde de corte
    rrect(draw, [0, 0, OUT_W - 1, OUT_H - 1], r=20, outline=C["border"], width=10)

    img.save(out_path, "PNG")
    print(f"  [OK] {os.path.basename(out_path)}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("[*] Generando cartas de tierras básicas...\n")
    for tierra in ["isla", "montana", "bosque", "llanura", "pantano"]:
        make_land_card(tierra, os.path.join(OUTPUT_DIR, f"{tierra}.png"))
    print(f"\n[OK] 5 cartas guardadas en pruebas/tierras/")
    print("[!] Revisar antes de mover a output/cartas/tierras/")
