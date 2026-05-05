#!/usr/bin/env python3
"""
download_artworks.py
Descarga los art_crop de Old School y Mid School desde Scryfall.

Lee:    data/cards_old_school.json  y  data/cards_mid_school.json
Guarda: data/artworks/<nombre_seguro>.jpg

Uso:
    python download_artworks.py            # ambas eras (~3800 cartas)
    python download_artworks.py --era old  # solo Old School (~800)
    python download_artworks.py --era mid  # solo Mid School (~3000)
    python download_artworks.py --force    # re-descarga aunque ya existan
"""

import json
import os
import sys
import time
import argparse
import requests

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(SCRIPT_DIR, "data")
ARTWORKS_DIR = os.path.join(DATA_DIR, "artworks")

# Scryfall pide cortesía: ~100ms entre peticiones de imágenes
DELAY = 0.08


def safe_name(name: str) -> str:
    for ch in (" ", "/", "'", ",", ":", '"', "?", "!"):
        name = name.replace(ch, "_")
    return name.strip("_")


def artwork_path(name: str) -> str:
    return os.path.join(ARTWORKS_DIR, safe_name(name) + ".jpg")


def download_one(name: str, url: str, dest: str, force: bool) -> str:
    """
    Retorna: 'skip' si ya existe, 'ok' si descargó, 'error' si falló.
    """
    if os.path.exists(dest) and not force:
        return "skip"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(dest, "wb") as f:
                f.write(r.content)
            return "ok"
        print(f"    [!] HTTP {r.status_code} — {name}")
        return "error"
    except Exception as e:
        print(f"    [!] {name}: {e}")
        return "error"


def download_era(cartas: list, tag: str, force: bool) -> tuple[int, int, int]:
    ok = skip = err = 0
    total = len(cartas)
    for i, carta in enumerate(cartas, 1):
        name = carta.get("name", "")
        url  = carta.get("art_crop", "")
        if not url:
            skip += 1
            continue

        dest   = artwork_path(name)
        result = download_one(name, url, dest, force)

        if result == "ok":
            ok += 1
            time.sleep(DELAY)
        elif result == "skip":
            skip += 1
        else:
            err += 1

        if i % 100 == 0 or i == total:
            pct = i / total * 100
            print(f"  [{tag}] {i}/{total} ({pct:.0f}%)  ok={ok}  cache={skip}  err={err}")

    return ok, skip, err


def load_json(path: str) -> list:
    if not os.path.exists(path):
        print(f"  [!] No existe: {path}")
        print(f"      Ejecuta primero: python download_card_database.py")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Descarga art_crop de Old School y Mid School")
    ap.add_argument("--era", choices=["old", "mid", "all"], default="all",
                    help="Era a descargar (default: all)")
    ap.add_argument("--force", "-f", action="store_true",
                    help="Re-descargar aunque la imagen ya exista localmente")
    args = ap.parse_args()

    os.makedirs(ARTWORKS_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("  MTG FORGE LAB — Descarga de Artworks")
    print("=" * 60)

    # Seleccionar fuentes según era
    path_old = os.path.join(DATA_DIR, "cards_old_school.json")
    path_mid = os.path.join(DATA_DIR, "cards_mid_school.json")

    cartas_old: list = []
    cartas_mid: list = []

    if args.era in ("old", "all"):
        cartas_old = load_json(path_old)
        print(f"  Old School : {len(cartas_old)} cartas")

    if args.era in ("mid", "all"):
        cartas_mid = load_json(path_mid)
        # Quitar los que ya están en Old School (comparten nombre)
        if cartas_old:
            nombres_old = {c["name"] for c in cartas_old}
            cartas_mid  = [c for c in cartas_mid if c["name"] not in nombres_old]
        print(f"  Mid School : {len(cartas_mid)} cartas únicas")

    total = len(cartas_old) + len(cartas_mid)
    ya    = len([f for f in os.listdir(ARTWORKS_DIR) if f.endswith(".jpg")])

    print(f"\n  Destino   : {ARTWORKS_DIR}")
    print(f"  Ya en disco: {ya} imágenes")
    print(f"  A procesar : {total} cartas", end="")
    print("  (--force: re-descarga todo)" if args.force else "  (omite las ya guardadas)")
    print()

    ok = skip = err = 0

    if cartas_old:
        print(f"[1/2] Old School ({len(cartas_old)} cartas)...")
        o, s, e = download_era(cartas_old, "OLD", args.force)
        ok += o; skip += s; err += e
        print(f"      Listo — {o} nuevas, {s} en cache, {e} errores\n")

    if cartas_mid:
        label = "2/2" if cartas_old else "1/1"
        print(f"[{label}] Mid School ({len(cartas_mid)} cartas)...")
        o, s, e = download_era(cartas_mid, "MID", args.force)
        ok += o; skip += s; err += e
        print(f"      Listo — {o} nuevas, {s} en cache, {e} errores\n")

    total_disco = len([f for f in os.listdir(ARTWORKS_DIR) if f.endswith(".jpg")])
    size_mb     = sum(
        os.path.getsize(os.path.join(ARTWORKS_DIR, f))
        for f in os.listdir(ARTWORKS_DIR) if f.endswith(".jpg")
    ) / 1024 / 1024

    print("=" * 60)
    print(f"  Descargadas : {ok}")
    print(f"  En cache    : {skip}")
    print(f"  Errores     : {err}")
    print(f"  Total disco : {total_disco} imágenes ({size_mb:.0f} MB)")
    print(f"  Carpeta     : {ARTWORKS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
