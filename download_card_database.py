#!/usr/bin/env python3
"""
download_card_database.py
Descarga todas las cartas de Old School y Mid School desde Scryfall bulk data.

Uso:
    python download_card_database.py

Genera:
    data/cards_old_school.json   (~800 cartas)
    data/cards_mid_school.json   (~3000 cartas)
    data/cards_all_eras.json     (ambas combinadas, sin duplicados)
"""

import json
import os
import sys
import time
import requests
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "data")

# ─── Sets por era (mismo que deck_builder.py) ─────────────────────────────────

SETS_OLD_SCHOOL = {
    "LEA", "LEB", "2ED", "ARN", "ATQ", "LEG", "DRK", "FEM"
}

SETS_MID_SCHOOL = {
    "ICE", "HML", "ALL", "MIR", "VIS", "WTH",
    "TMP", "STH", "EXO", "USG", "ULG", "UDS",
    "MMQ", "NMS", "PCY", "INV", "PLS", "APC",
    "ODY", "TOR", "JUD", "ONS", "LGN", "SCG",
}

# Campos que nos interesan (el resto se descarta para ahorrar espacio)
CAMPOS = {
    "name", "mana_cost", "cmc", "type_line", "oracle_text",
    "colors", "color_identity", "set", "collector_number",
    "rarity", "power", "toughness", "keywords", "image_uris",
    "layout", "legalities",
}


# ─── Descarga ─────────────────────────────────────────────────────────────────

def obtener_url_bulk() -> str:
    """Obtiene la URL del archivo bulk 'default_cards' de Scryfall."""
    print("  Consultando Scryfall bulk-data endpoint...")
    resp = requests.get("https://api.scryfall.com/bulk-data", timeout=15)
    resp.raise_for_status()
    for item in resp.json()["data"]:
        if item["type"] == "default_cards":
            size = item.get("compressed_size") or item.get("size") or 0
            size_mb = size / 1024 / 1024
            print(f"  Archivo: {item['name']} ({size_mb:.0f} MB)")
            return item["download_uri"]
    raise RuntimeError("No se encontró el bulk data 'default_cards' en Scryfall.")


def descargar_bulk(url: str) -> list:
    """Descarga el JSON completo de Scryfall con todas las cartas."""
    print(f"  Descargando... (puede tardar 1-2 minutos)")
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    descargado = 0
    chunks = []

    for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
        chunks.append(chunk)
        descargado += len(chunk)
        if total:
            pct = descargado / total * 100
            mb  = descargado / 1024 / 1024
            print(f"\r  Progreso: {mb:.0f} MB ({pct:.0f}%)", end="", flush=True)

    print()
    print("  Parseando JSON...")
    return json.loads(b"".join(chunks))


# ─── Filtrado ─────────────────────────────────────────────────────────────────

def filtrar_campos(carta: dict) -> dict:
    """Conserva solo los campos relevantes de una carta."""
    resultado = {k: carta.get(k) for k in CAMPOS if k in carta}

    # Extraer solo la URL del art_crop para no guardar todo image_uris
    if "image_uris" in resultado and resultado["image_uris"]:
        resultado["art_crop"] = resultado["image_uris"].get("art_crop", "")
    resultado.pop("image_uris", None)

    return resultado


def filtrar_por_era(todas: list, sets_era: set) -> list:
    """Filtra cartas por set y elimina tokens/variantes no jugables."""
    cartas = []
    nombres_vistos = set()

    for carta in todas:
        set_code = (carta.get("set") or "").upper()
        if set_code not in sets_era:
            continue

        # Excluir tokens, emblemas, y layouts raros
        layout = carta.get("layout", "")
        if layout in {"token", "emblem", "art_series", "double_faced_token"}:
            continue

        # Excluir cartas con nombre duplicado (quedarse con la primera impresión en la era)
        nombre = carta.get("name", "")
        if nombre in nombres_vistos:
            continue
        nombres_vistos.add(nombre)

        cartas.append(filtrar_campos(carta))

    return sorted(cartas, key=lambda c: c.get("name", ""))


# ─── Búsqueda local ───────────────────────────────────────────────────────────

def buscar_en_db(nombre: str, db: list, exacto: bool = True) -> Optional[dict]:
    """
    Busca una carta en la base local.
    exacto=True  → coincidencia exacta de nombre (insensible a mayúsculas)
    exacto=False → búsqueda por subcadena en nombre, tipo u oracle_text
    """
    nombre_lower = nombre.lower()
    for carta in db:
        if exacto:
            if carta.get("name", "").lower() == nombre_lower:
                return carta
        else:
            if (nombre_lower in carta.get("name", "").lower() or
                nombre_lower in carta.get("oracle_text", "").lower() or
                nombre_lower in carta.get("type_line", "").lower()):
                return carta
    return None


def buscar_por_keyword(keyword: str, db: list) -> list:
    """
    Busca cartas cuyo oracle_text, nombre o tipo contenga el keyword.
    Devuelve lista ordenada por nombre.
    """
    keyword_lower = keyword.lower()
    resultados = []
    for carta in db:
        if (keyword_lower in carta.get("oracle_text", "").lower() or
            keyword_lower in carta.get("name", "").lower() or
            keyword_lower in carta.get("type_line", "").lower()):
            resultados.append(carta)
    return resultados


# ─── Guardar / Cargar ─────────────────────────────────────────────────────────

def guardar_json(cartas: list, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cartas, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(path) / 1024
    print(f"  Guardado: {path} ({len(cartas)} cartas, {size_kb:.0f} KB)")


def cargar_db(path: str) -> list:
    """Carga la base de datos local. Devuelve lista vacía si no existe."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    path_old   = os.path.join(DATA_DIR, "cards_old_school.json")
    path_mid   = os.path.join(DATA_DIR, "cards_mid_school.json")
    path_all   = os.path.join(DATA_DIR, "cards_all_eras.json")

    print("\n" + "=" * 60)
    print("  MTG FORGE LAB — Descarga de Base de Datos Local")
    print("=" * 60)

    # Verificar si ya existe
    if os.path.exists(path_all):
        db = cargar_db(path_all)
        print(f"\n  Ya existe base local: {len(db)} cartas en cards_all_eras.json")
        resp = input("  ¿Descargar de nuevo para actualizar? (s/N): ").strip().lower()
        if resp != "s":
            print("  Usando base existente. Saliendo.")
            return

    # Descargar
    print("\n[1/4] Obteniendo URL de Scryfall bulk data...")
    url = obtener_url_bulk()

    print("\n[2/4] Descargando todas las cartas de Scryfall...")
    todas = descargar_bulk(url)
    print(f"  Total cartas en Scryfall: {len(todas):,}")

    # Filtrar por era
    print("\n[3/4] Filtrando por era...")
    old_school = filtrar_por_era(todas, SETS_OLD_SCHOOL)
    mid_school = filtrar_por_era(todas, SETS_MID_SCHOOL)

    # Combinar sin duplicados para cards_all_eras
    nombres_old = {c["name"] for c in old_school}
    mid_sin_dup = [c for c in mid_school if c["name"] not in nombres_old]
    todas_eras  = sorted(old_school + mid_sin_dup, key=lambda c: c.get("name", ""))

    print(f"  Old School : {len(old_school):,} cartas únicas")
    print(f"  Mid School : {len(mid_school):,} cartas únicas")
    print(f"  Combinadas : {len(todas_eras):,} cartas únicas (sin duplicados)")

    # Guardar
    print("\n[4/4] Guardando archivos...")
    guardar_json(old_school, path_old)
    guardar_json(mid_school, path_mid)
    guardar_json(todas_eras, path_all)

    print("\n" + "=" * 60)
    print("  ¡Base de datos lista!")
    print(f"  Úsala con: from download_card_database import cargar_db, buscar_por_keyword")
    print("=" * 60)


if __name__ == "__main__":
    main()
