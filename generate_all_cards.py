#!/usr/bin/env python3
"""
generate_all_cards.py
Genera TODAS las cartas de Old School y Mid School en formato Old Border.

Lee:    data/cards_all_eras.json  (o por era individual)
Usa:    data/artworks/<nombre>.jpg  si existen (sin llamar a Scryfall)
Genera: output/cartas/{color}/{nombre}.png
Traduce: Scryfall ES oficial primero (gratis), Google Translate solo como fallback

Reanudable: omite cartas cuyo PNG ya existe (a menos que --force).

Uso:
    python generate_all_cards.py               # todas (~3800 cartas)
    python generate_all_cards.py --era old     # solo Old School (~800)
    python generate_all_cards.py --era mid     # solo Mid School (~3000)
    python generate_all_cards.py --batch 100   # procesa las primeras 100 sin PNG
    python generate_all_cards.py --force       # regenera aunque el PNG exista
    python generate_all_cards.py --no-gt       # sin Google Translate (solo Scryfall ES)
"""

import json
import os
import sys
import time
import argparse

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, "output")
CARTAS_DIR  = os.path.join(OUTPUT_DIR, "cartas")
TRANS_PATH  = os.path.join(DATA_DIR, "mtg_translations_es.json")

COLOR_SUBDIRS = ("azul", "blanco", "cafe", "multicolor", "negro", "rojo", "tierras", "verde")

# ─── Importar módulos del proyecto ────────────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
from make_cards_old_border import make_card_old, _folder_color, MARCOS_DIR
from translator import translate_card, translate_type_line

import re


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_name(name: str) -> str:
    return name.replace(" ", "_").replace("/", "-")


def png_path(name: str, mana_cost: str, is_land: bool) -> str:
    folder = _folder_color(mana_cost, is_land)
    return os.path.join(CARTAS_DIR, folder, safe_name(name) + ".png")


def is_land(type_line: str) -> bool:
    return "Land" in type_line


def is_basic_land(type_line: str) -> bool:
    return "Basic Land" in type_line


def has_special_land_frame() -> bool:
    return os.path.exists(os.path.join(MARCOS_DIR, "marco_tierra_especial_vacio.png"))


# ─── Carga de base de datos ────────────────────────────────────────────────────

def load_cards(era: str) -> list:
    if era == "old":
        paths = [os.path.join(DATA_DIR, "cards_old_school.json")]
    elif era == "mid":
        paths = [os.path.join(DATA_DIR, "cards_mid_school.json")]
    else:
        paths = [os.path.join(DATA_DIR, "cards_all_eras.json")]

    for p in paths:
        if not os.path.exists(p):
            print(f"[!] No existe {p}. Ejecuta: python download_card_database.py")
            sys.exit(1)

    cartas = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            cartas.extend(json.load(f))

    # Deduplicar por nombre (por si se cargaron ambas eras por separado)
    seen, unique = set(), []
    for c in cartas:
        if c["name"] not in seen:
            seen.add(c["name"])
            unique.append(c)

    return unique


# ─── Traducción con caché ──────────────────────────────────────────────────────

def load_translations() -> dict:
    if os.path.exists(TRANS_PATH):
        with open(TRANS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_translations(db: dict) -> None:
    with open(TRANS_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_translation(carta: dict, trans_db: dict, use_gt: bool) -> dict:
    """
    Devuelve la traducción de la carta.
    Estrategia: caché local → Scryfall ES (gratis) → Google Translate (opcional).
    Guarda en caché automáticamente.
    """
    name      = carta["name"]
    mana_cost = carta.get("mana_cost", "")
    type_line = carta.get("type_line", "")
    oracle    = carta.get("oracle_text", "")

    # 1. Caché local
    cached = trans_db.get(name)
    if cached and cached.get("text_es") is not None:
        # Asegurar mana_cost en caché
        if not cached.get("mana_cost"):
            cached["mana_cost"] = mana_cost
        return cached

    # 2. Traducir (Scryfall ES → Google Translate si allow)
    if not use_gt:
        # Solo tabla fija + Scryfall ES
        import requests as _req
        url = f"https://api.scryfall.com/cards/named?exact={_req.utils.quote(name)}&lang=es"
        try:
            r = _req.get(url, timeout=10)
            time.sleep(0.12)
            if r.status_code == 200:
                d = r.json()
                if d.get("printed_text"):
                    result = {
                        "name_es":  d.get("printed_name") or name,
                        "type_es":  d.get("printed_type_line") or translate_type_line(type_line),
                        "text_es":  d.get("printed_text") or "",
                        "mana_cost": mana_cost,
                    }
                    trans_db[name] = result
                    return result
        except Exception:
            pass
        # Sin GT: usar solo tabla fija para tipo
        result = {
            "name_es":  name,
            "type_es":  translate_type_line(type_line),
            "text_es":  oracle,   # texto en inglés si no hay ES
            "mana_cost": mana_cost,
        }
        trans_db[name] = result
        return result

    # Con Google Translate habilitado
    result = translate_card(name, oracle, type_line)
    result["mana_cost"] = mana_cost
    trans_db[name] = result
    return result


# ─── Generar una carta ────────────────────────────────────────────────────────

def generate_card(carta: dict, tr: dict, out_path: str) -> bool:
    """Llama a make_card_old y devuelve True si tuvo éxito."""
    type_line  = carta.get("type_line", "")
    is_creature = "Creature" in type_line
    try:
        make_card_old(
            name_orig = carta["name"],
            tr        = tr,
            image_url = carta.get("art_crop", ""),
            power     = carta.get("power")     if is_creature else None,
            toughness = carta.get("toughness") if is_creature else None,
            out       = out_path,
        )
        return True
    except Exception as e:
        print(f"    [!] Error generando {carta['name']}: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Genera todas las cartas MTG en formato Old Border")
    ap.add_argument("--era", choices=["old", "mid", "all"], default="all",
                    help="Era a procesar (default: all)")
    ap.add_argument("--batch", "-b", type=int, metavar="N",
                    help="Procesar solo las primeras N cartas sin PNG (reanudable)")
    ap.add_argument("--force", "-f", action="store_true",
                    help="Regenerar PNGs aunque ya existan")
    ap.add_argument("--no-gt", action="store_true",
                    help="Deshabilitar Google Translate (usa solo Scryfall ES + tablas fijas)")
    args = ap.parse_args()

    # Crear carpetas de salida
    for sub in COLOR_SUBDIRS:
        os.makedirs(os.path.join(CARTAS_DIR, sub), exist_ok=True)

    print("\n" + "=" * 60)
    print("  MTG FORGE LAB — Generación Masiva Old Border")
    print("=" * 60)

    # Cargar base de datos
    print(f"\n[1/3] Cargando base de datos ({args.era})...")
    cartas = load_cards(args.era)
    print(f"  {len(cartas)} cartas en total")

    # Separar tierras básicas (las maneja make_land_cards.py)
    basicas    = [c for c in cartas if is_basic_land(c.get("type_line", ""))]
    no_basicas = [c for c in cartas if not is_basic_land(c.get("type_line", ""))]

    # Tierras no básicas: solo si existe marco_tierra_especial_vacio.png
    tierras_especiales = [c for c in no_basicas if is_land(c.get("type_line", ""))]
    no_tierras         = [c for c in no_basicas if not is_land(c.get("type_line", ""))]

    tiene_marco_tierra = has_special_land_frame()

    if tierras_especiales and not tiene_marco_tierra:
        print(f"  [!] {len(tierras_especiales)} tierras no básicas omitidas "
              f"(falta marco_tierra_especial_vacio.png)")

    # Candidatas a generar
    candidatas = no_tierras
    if tiene_marco_tierra:
        candidatas = candidatas + tierras_especiales

    print(f"  Tierras básicas  : {len(basicas)} (usa make_land_cards.py)")
    print(f"  Tierras especiales: {len(tierras_especiales)}"
          + (" [incluidas]" if tiene_marco_tierra else " [omitidas]"))
    print(f"  Hechizos/criaturas/artefactos: {len(no_tierras)}")
    print(f"  A procesar: {len(candidatas)} cartas")
    if args.no_gt:
        print("  Modo: Scryfall ES + tablas fijas (sin Google Translate)")
    else:
        print("  Modo: Scryfall ES → Google Translate como fallback")

    # Determinar cuáles necesitan generarse
    pendientes = []
    ya_hechas  = 0
    for c in candidatas:
        mana  = c.get("mana_cost", "")
        land  = is_land(c.get("type_line", ""))
        out   = png_path(c["name"], mana, land)
        if os.path.exists(out) and not args.force:
            ya_hechas += 1
        else:
            pendientes.append((c, out))

    print(f"\n  Ya generadas : {ya_hechas}")
    print(f"  Pendientes   : {len(pendientes)}")

    if not pendientes:
        print("\n  Nada que hacer. Usa --force para regenerar.")
        return

    if args.batch and len(pendientes) > args.batch:
        print(f"  [BATCH] Procesando solo las primeras {args.batch} de {len(pendientes)}")
        pendientes = pendientes[:args.batch]

    # Cargar caché de traducciones
    print("\n[2/3] Cargando traducciones...")
    trans_db = load_translations()
    con_cache = sum(1 for c, _ in pendientes if c["name"] in trans_db
                    and trans_db[c["name"]].get("text_es"))
    sin_cache = len(pendientes) - con_cache
    print(f"  En caché : {con_cache}")
    print(f"  A traducir: {sin_cache} (cada una = 1 llamada Scryfall ES + GT si falla)")

    # Generar
    print(f"\n[3/3] Generando {len(pendientes)} cartas...\n")
    ok = err = 0
    trans_guardadas = 0
    t0 = time.time()

    for i, (carta, out_path) in enumerate(pendientes, 1):
        name = carta["name"]
        tipo = carta.get("type_line", "")

        # Traducción
        tr = get_translation(carta, trans_db, use_gt=not args.no_gt)

        # Generar PNG
        print(f"  [{i}/{len(pendientes)}] {name}")
        exito = generate_card(carta, tr, out_path)
        if exito:
            ok += 1
        else:
            err += 1

        # Guardar traducciones cada 25 cartas
        if i % 25 == 0:
            save_translations(trans_db)
            trans_guardadas = i
            elapsed = time.time() - t0
            rate    = i / elapsed
            remain  = (len(pendientes) - i) / rate if rate > 0 else 0
            mins    = int(remain // 60)
            secs    = int(remain % 60)
            print(f"\n  --- Progreso: {i}/{len(pendientes)} | "
                  f"{ok} ok, {err} err | "
                  f"~{mins}m {secs}s restantes ---\n")

    # Guardar traducciones pendientes
    save_translations(trans_db)

    elapsed = time.time() - t0
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    pendientes_totales = len([c for c in candidatas
                              if not os.path.exists(
                                  png_path(c["name"], c.get("mana_cost",""),
                                           is_land(c.get("type_line",""))))])

    print("\n" + "=" * 60)
    print(f"  Generadas OK : {ok}")
    print(f"  Errores      : {err}")
    print(f"  Tiempo       : {mins}m {secs}s")
    print(f"  PNGs en      : {CARTAS_DIR}/")
    if pendientes_totales > 0:
        print(f"\n  Faltan {pendientes_totales} cartas. Vuelve a ejecutar para continuar.")
        print(f"  (o usa --batch N para procesar de a grupos)")
    else:
        print("\n  ¡Todas las cartas generadas!")
    print("=" * 60)


if __name__ == "__main__":
    main()
