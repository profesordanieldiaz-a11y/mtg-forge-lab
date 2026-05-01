#!/usr/bin/env python3
"""
MTG Deck Builder -- Old School / Mid School
Busca cartas via Scryfall API y construye mazos completos en formato Moxfield.

Uso:
    python deck_builder.py                        # Modo interactivo
    python deck_builder.py -a descarte -e old_school -o mazo.txt
    python deck_builder.py -a burn -e mid_school --formato json
"""

import requests
import json
import time
import sys
import argparse
import os
import subprocess
from collections import defaultdict

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- DEFINICIÓN DE ERAS -------------------------------------------------------

ERAS = {
    "old_school": {
        "nombre": "Old School (93/94)",
        "sets": ["LEA", "LEB", "2ED", "ARN", "ATQ", "LEG", "DRK", "FEM"],
        "filtro_scryfall": "(e:lea OR e:leb OR e:2ed OR e:arn OR e:atq OR e:leg OR e:drk OR e:fem)",
        "descripcion": "Alpha * Beta * Unlimited * Arabian Nights * Antiquities * Legends * The Dark * Fallen Empires",
    },
    "mid_school": {
        "nombre": "Mid School (95-03)",
        "sets": [
            "ICE", "HML", "ALL", "MIR", "VIS", "WTH",
            "TMP", "STH", "EXO", "USG", "ULG", "UDS",
            "MMQ", "NMS", "PCY", "INV", "PLS", "APC",
            "ODY", "TOR", "JUD", "ONS", "LGN", "SCG",
        ],
        "filtro_scryfall": "year>=1995 year<=2003 -e:4ed -e:5ed -e:6ed -e:7ed -e:8ed",
        "descripcion": "Ice Age * Alliances * Mirage Block * Tempest Block * Urza Block * "
                       "Masques Block * Invasion Block * Odyssey Block * Onslaught Block",
    },
    "ambos": {
        "nombre": "Old School + Mid School (93-03)",
        "sets": [],
        "filtro_scryfall": "year<=2003",
        "descripcion": "Alpha (1993) hasta Scourge (2003)",
    },
}

# --- STAPLES CONOCIDOS POR ARQUETIPO/ERA -------------------------------------
# Cartas curadas manualmente como punto de partida para cada arquetipo.
# Se verifican en Scryfall para obtener set/collector_number exactos.

STAPLES = {
    # Nota: NO incluir tierras básicas aquí. Phase 3 las añade automáticamente.
    # Tierras no-básicas especiales SÍ se incluyen (Strip Mine, etc.)
    # Límite recomendado: ~36-38 cartas no-tierra en total.

    "descarte": {
        "old_school": {
            "nucleo": [
                ("Hymn to Tourach", 4),        # FEM -- Discard 2 al azar
                ("Mind Twist", 1),              # LEA -- X discard (restricted)
                ("Hypnotic Specter", 4),        # LEA -- Discard al dañar
                ("The Rack", 4),                # DRK -- Daño por manos pequeñas
                ("Disrupting Scepter", 3),      # LEA -- Tap: descarta
                ("Dark Ritual", 4),             # LEA -- Aceleración de maná
                ("Demonic Tutor", 1),           # LEA -- Buscar (restricted)
                ("Sinkhole", 4),                # LEA -- Land destruction
                ("Nether Void", 2),             # LEG -- Tax todos los hechizos
                ("Library of Leng", 1),         # ATQ -- Sinergía descarte
            ],
            "apoyo": [
                ("Strip Mine", 4),              # ATQ -- Land destruction (tierra)
                ("Maze of Ith", 1),             # DRK -- Defensa (tierra)
                ("Black Knight", 4),            # LEA -- Cuerpo agresivo
                ("Order of the Ebon Hand", 4),  # FEM -- Cuerpo agresivo
                ("Erg Raiders", 2),             # ARN -- Cuerpo económico
            ],
        },
        "mid_school": {
            "nucleo": [
                ("Cabal Therapy", 4),           # JUD -- Discard nombrado (free)
                ("Duress", 4),                  # UDS -- Discard no-criatura
                ("Unmask", 2),                  # MMQ -- Discard gratis
                ("Ravenous Rats", 4),           # EXO -- Criatura: descarta
                ("Mesmeric Fiend", 4),          # TOR -- Criatura: exilia carta
                ("Funeral Charm", 4),           # MIR -- Instant discard
                ("Zombie Infestation", 2),      # ODY -- Sinergía descarte
                ("Cabal Conditioning", 2),      # ODY -- Mass discard
                ("Dark Ritual", 4),             # LEA -- Aceleración
            ],
            "apoyo": [
                ("Cabal Coffers", 2),           # TOR -- Mana engine (tierra)
                ("Shadowmage Infiltrator", 3),  # ODY -- Draw al dañar
                ("Phyrexian Rager", 3),         # INV -- ETB draw
            ],
        },
    },
    "burn": {
        "old_school": {
            "nucleo": [
                ("Lightning Bolt", 4),          # LEA -- 3 dmg por R
                ("Chain Lightning", 4),         # LEG -- 3 dmg por R
                ("Fireball", 2),                # LEA -- X daño
                ("Wheel of Fortune", 1),        # LEA -- Restricted
                ("Fork", 2),                    # LEA -- Copiar hechizo
                ("Ball Lightning", 4),          # DRK -- 6/1 haste trample
                ("Mons's Goblin Raiders", 4),   # LEA -- Aggro 1-drop
                ("Ironclaw Orcs", 4),           # LEG -- Cuerpo sólido
                ("Sedge Troll", 3),             # LEA -- Regeneración
                ("Shivan Dragon", 2),           # LEA -- Amenaza final
            ],
            "apoyo": [
                ("Strip Mine", 4),              # ATQ -- Land destruction (tierra)
            ],
        },
        "mid_school": {
            "nucleo": [
                ("Lightning Bolt", 4),          # Reimpreso
                ("Incinerate", 4),              # ICE -- 3 dmg + previene regen
                ("Firebolt", 4),                # ODY -- Flashback
                ("Fireblast", 4),               # VIS -- Sacrificar 2 mountains
                ("Reckless Abandon", 4),        # EXO -- Sacrificio + daño
                ("Jackal Pup", 4),              # TMP -- Aggro 2/1 por R
                ("Mogg Fanatic", 4),            # TMP -- Sacrifice: 1 dmg
                ("Goblin Raider", 4),           # USG -- Cuerpo sólido
            ],
            "apoyo": [
                ("Cursed Scroll", 2),           # TMP -- Late game removal
                ("Goblin Cadets", 4),           # STH -- Aggro 1-drop
            ],
        },
    },
    "control_azul": {
        "old_school": {
            "nucleo": [
                ("Counterspell", 4),            # LEA -- 2-mana hard counter
                ("Mana Drain", 4),              # LEG -- Counter + mana
                ("Power Sink", 3),              # LEA -- Counter o tap
                ("Braingeyser", 2),             # LEA -- Draw X (restricted)
                ("Ancestral Recall", 1),        # LEA -- Restricted
                ("Time Walk", 1),               # LEA -- Restricted
                ("Unsummon", 3),                # LEA -- Bounce barato
                ("Psionic Blast", 3),           # LEA -- 4 dmg + 2 a ti
                ("Clone", 2),                   # LEA -- Copia criatura
                ("Air Elemental", 3),           # LEA -- Amenaza de vuelo
            ],
            "apoyo": [
                ("Black Lotus", 1),             # LEA -- Restricted (artefacto)
                ("Mox Sapphire", 1),            # LEA -- Restricted (artefacto)
                ("Sol Ring", 1),                # LEA -- Restricted (artefacto)
                ("Strip Mine", 4),              # ATQ -- Land destruction (tierra)
            ],
        },
        "mid_school": {
            "nucleo": [
                ("Counterspell", 4),
                ("Accumulated Knowledge", 4),   # NMS -- Draw escala
                ("Fact or Fiction", 4),         # INV -- Impulsión profunda
                ("Forbid", 3),                  # EXO -- Counter con buyback
                ("Mana Leak", 4),               # INV -- Counter económico
                ("Ophidian", 4),                # MIR -- Draw al dañar
                ("Morphling", 2),               # USG -- Criatura definitiva
                ("Thieving Magpie", 3),         # EXO -- Draw evasivo
                ("Deep Analysis", 4),           # TOR -- Draw con flashback
            ],
            "apoyo": [
                ("Faerie Conclave", 3),         # ULG -- Tierra/criatura (tierra)
                ("Stalking Stones", 2),         # MIR -- Tierra/criatura (tierra)
            ],
        },
    },
    "aggro_negro": {
        "old_school": {
            "nucleo": [
                ("Black Knight", 4),            # LEA -- 2/2 first strike protection
                ("Order of the Ebon Hand", 4),  # FEM -- Similar a Black Knight
                ("Hypnotic Specter", 4),        # LEA -- Evasión + discard
                ("Nether Shadow", 4),           # LEA -- Recursión rápida
                ("Drudge Skeletons", 3),        # LEA -- Regeneración barata
                ("Dark Ritual", 4),             # LEA -- Aceleración
                ("Dark Banishing", 3),          # DRK -- Removal
                ("Terror", 4),                  # LEA -- Removal barato
                ("Pestilence", 3),              # LEA -- Board wipe controlado
                ("Gloom", 3),                   # LEA -- Hostigador blanco
            ],
            "apoyo": [
                ("Strip Mine", 4),              # ATQ -- Land destruction (tierra)
            ],
        },
        "mid_school": {
            "nucleo": [
                ("Carnophage", 4),              # EXO -- 2/2 por B
                ("Sarcomancy", 4),              # MIR -- Token zombie 2/2
                ("Hatred", 2),                  # EXO -- Pump para OTK
                ("Phyrexian Negator", 4),       # UDS -- 5/5 trample por 2BB
                ("Dark Ritual", 4),             # Aceleración
                ("Duress", 4),                  # UDS -- Disruption
                ("Smother", 4),                 # ONS -- Removal
                ("Consume Spirit", 3),          # MIR -- Drain
                ("Stromgald Cabal", 3),         # ICE -- Protection from white
                ("Funeral Charm", 4),           # MIR -- Flexible instant
            ],
            "apoyo": [
                ("Cabal Coffers", 2),           # TOR -- Mana engine (tierra)
            ],
        },
    },
    "stompy_verde": {
        "old_school": {
            "nucleo": [
                ("Llanowar Elves", 4),          # LEA -- Mana dork
                ("Elvish Archers", 4),          # LEA -- 2/1 first strike
                ("Argothian Pixies", 3),        # ATQ -- Protection artifacts
                ("Craw Wurm", 3),               # LEA -- Gran criatura
                ("Untamed Wilds", 3),           # LEG -- Fetch básica
                ("Regrowth", 1),                # LEA -- Restricted
                ("Desert Twister", 2),          # ARN -- Removal universal
                ("Fog", 3),                     # LEA -- Prevenir daño
                ("Giant Growth", 4),            # LEA -- Pump barato
                ("Juggernaut", 4),              # LEA -- Artefacto agresivo
            ],
            "apoyo": [
                ("Strip Mine", 4),              # ATQ -- Land destruction (tierra)
            ],
        },
        "mid_school": {
            "nucleo": [
                ("Llanowar Elves", 4),
                ("Fyndhorn Elves", 4),          # ICE -- Copia de Llanowar
                ("Elvish Spirit Guide", 3),     # ALL -- Exile para G
                ("Albino Troll", 4),            # MIR -- 3/3 con echo
                ("Groundbreaker", 3),           # PLS -- 6/1 trample haste
                ("Rancor", 4),                  # ULG -- Encantamiento pump
                ("Plow Under", 3),              # USG -- Bounce 2 lands
                ("Quirion Ranger", 4),          # VIS -- Untap elfo
                ("River Boa", 4),               # MIR -- Islandwalk + regen
                ("Skyshroud Elite", 4),         # EXO -- 2/1 o 3/2
            ],
            "apoyo": [
                ("Treetop Village", 3),         # ULG -- Tierra/criatura (tierra)
            ],
        },
    },
}

# --- SCRYFALL API -------------------------------------------------------------

SCRYFALL_BASE = "https://api.scryfall.com"
_cache_scryfall: dict = {}


def _request_with_backoff(url: str, params: dict = None, max_retries: int = 5):
    """Hace una request con backoff exponencial ante 429."""
    delay = 0.2
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"  [rate limit] Esperando {wait:.1f}s...")
                time.sleep(wait)
                continue
            return resp
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))
            else:
                print(f"  [!] Error de red: {e}")
    return None


def _get_card_scryfall(name: str, era_sets: list = None, era_key: str = "all"):
    """
    Busca una carta. Prioridad:
      1. Base de datos local (instantáneo, sin API)
      2. Scryfall API (fallback si no está en la DB)
    """
    key = f"{name}|{','.join(era_sets or [])}"
    if key in _cache_scryfall:
        return _cache_scryfall[key]

    # Intento 1: base local
    local = _buscar_en_db_local(name, era_key)
    if local:
        print(f"    [DB local] {name}")
        _cache_scryfall[key] = local
        return local

    # Intento 2: Scryfall API — impresión en la era
    if era_sets:
        sets_filter = " OR ".join(f"e:{s.lower()}" for s in era_sets)
        query = f'!"{name}" ({sets_filter})'
        resp = _request_with_backoff(
            f"{SCRYFALL_BASE}/cards/search",
            params={"q": query, "unique": "prints", "order": "released"},
        )
        time.sleep(0.15)
        if resp and resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                _cache_scryfall[key] = data[0]
                return data[0]

    # Intento 3: Scryfall API — cualquier impresión
    resp = _request_with_backoff(f"{SCRYFALL_BASE}/cards/named", params={"exact": name})
    time.sleep(0.15)
    if resp and resp.status_code == 200:
        card = resp.json()
        _cache_scryfall[key] = card
        return card

    _cache_scryfall[key] = None
    return None


def _scryfall_search(query: str, max_results: int = 30) -> list:
    """Busca cartas en Scryfall con query avanzada."""
    cards = []
    url = f"{SCRYFALL_BASE}/cards/search"
    params = {"q": query, "order": "edhrec", "unique": "cards"}

    while url and len(cards) < max_results:
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            if data.get("object") == "error":
                break
            cards.extend(data.get("data", []))
            url = data.get("next_page")
            params = {}
            time.sleep(0.1)
        except Exception as e:
            print(f"  [!] Error Scryfall: {e}")
            break

    return cards[:max_results]


def _buscar_cartas_adicionales(arquetipo_key: str, era: dict, cantidad_faltante: int) -> list:
    """Busca cartas adicionales en Scryfall para completar el mazo."""
    filtro_era = era["filtro_scryfall"]
    consultas_por_arquetipo = {
        "descarte": [
            f"o:discard c:b {filtro_era} -t:land",
            f"o:\"your hand\" c:b {filtro_era} -t:land",
            f"o:\"target player discards\" {filtro_era} -t:land",
        ],
        "burn": [
            f"o:damage c:r t:instant {filtro_era}",
            f"o:damage c:r t:sorcery {filtro_era}",
            f"c:r t:creature mv<=2 {filtro_era}",
        ],
        "control_azul": [
            f"o:counter t:instant c:u {filtro_era}",
            f"o:\"draw\" t:instant c:u {filtro_era}",
            f"c:u t:creature o:flying {filtro_era}",
        ],
        "aggro_negro": [
            f"c:b t:creature mv<=2 {filtro_era}",
            f"o:\"first strike\" c:b t:creature {filtro_era}",
            f"c:b t:instant o:destroy {filtro_era}",
        ],
        "stompy_verde": [
            f"c:g t:creature mv<=2 {filtro_era}",
            f"o:trample c:g t:creature {filtro_era}",
            f"c:g t:instant o:\"target creature\" {filtro_era}",
        ],
    }

    queries = consultas_por_arquetipo.get(arquetipo_key, [])
    encontradas = []
    for q in queries:
        resultados = _scryfall_search(q, max_results=20)
        for card in resultados:
            encontradas.append((card.get("name", ""), 1, card))
        if len(encontradas) >= cantidad_faltante * 3:
            break
    return encontradas


# --- CONSTRUCCIÓN DEL MAZO ----------------------------------------------------

def construir_mazo(arquetipo_key: str, era_key: str) -> dict:
    """Construye un mazo completo de 60 cartas para el arquetipo y era dados."""
    era = ERAS[era_key]
    era_sets = era["sets"]
    staples_era = STAPLES[arquetipo_key].get(era_key, STAPLES[arquetipo_key].get("old_school", {}))

    print(f"\n{'='*60}")
    print(f"  ARQUETIPO : {arquetipo_key.upper().replace('_', ' ')}")
    print(f"  ERA       : {era['nombre']}")
    print(f"  SETS      : {era['descripcion'][:55]}...")
    print(f"{'='*60}\n")

    deck_cartas = []
    usados = set()
    total_no_tierras = 0
    total_tierras = 0

    # -- Fase 1: Agregar staples curados --------------------------------------
    print("  [1/3] Verificando staples curados en Scryfall...\n")

    for seccion_key in ["nucleo", "apoyo"]:
        seccion = staples_era.get(seccion_key, [])
        if not seccion:
            continue
        etiqueta = "NÚCLEO" if seccion_key == "nucleo" else "APOYO"
        print(f"  -- {etiqueta} --")

        for nombre, copias in seccion:
            if nombre in usados:
                continue

            card_data = _get_card_scryfall(nombre, era_sets if era_sets else None, era_key)

            if card_data:
                set_code = card_data.get("set", "???").upper()
                col_num = card_data.get("collector_number", "")
                tipo = card_data.get("type_line", "")
                es_tierra = "Land" in tipo

                entrada = {
                    "nombre": nombre,
                    "copias": copias,
                    "set_code": set_code,
                    "collector_number": col_num,
                    "tipo": tipo,
                    "es_tierra": es_tierra,
                    "mana_cost": card_data.get("mana_cost", ""),
                    "cmc": card_data.get("cmc", 0),
                    "seccion": "mainboard",
                    "fuente": "curado",
                }
                deck_cartas.append(entrada)
                usados.add(nombre)

                if es_tierra:
                    total_tierras += copias
                else:
                    total_no_tierras += copias

                icono = "  " if es_tierra else ""
                print(f"    {icono}+ {copias}x {nombre} ({set_code}) {card_data.get('mana_cost','')}")
            else:
                print(f"    [?] No encontrada: {nombre}")

    # -- Fase 2: Completar con búsqueda Scryfall si faltan cartas -------------
    objetivo_no_tierras = 38
    objetivo_tierras = 22
    faltantes_no_tierras = max(0, objetivo_no_tierras - total_no_tierras)
    faltantes_tierras = max(0, objetivo_tierras - total_tierras)

    if faltantes_no_tierras > 0:
        print(f"\n  [2/3] Buscando {faltantes_no_tierras} cartas adicionales en Scryfall...\n")
        adicionales = _buscar_cartas_adicionales(arquetipo_key, era, faltantes_no_tierras)

        agregadas = 0
        for nombre, _, card_data in adicionales:
            if agregadas >= faltantes_no_tierras:
                break
            if nombre in usados:
                continue

            set_code = card_data.get("set", "???").upper()
            col_num = card_data.get("collector_number", "")
            tipo = card_data.get("type_line", "")
            cmc = card_data.get("cmc", 0)
            copias = 4 if cmc <= 1 else (3 if cmc == 2 else (2 if cmc <= 4 else 1))
            copias = min(copias, faltantes_no_tierras - agregadas)

            entrada = {
                "nombre": nombre,
                "copias": copias,
                "set_code": set_code,
                "collector_number": col_num,
                "tipo": tipo,
                "es_tierra": False,
                "mana_cost": card_data.get("mana_cost", ""),
                "cmc": cmc,
                "seccion": "mainboard",
                "fuente": "scryfall",
            }
            deck_cartas.append(entrada)
            usados.add(nombre)
            total_no_tierras += copias
            agregadas += copias
            print(f"    + {copias}x {nombre} ({set_code}) {card_data.get('mana_cost','')}")

    # -- Fase 3: Calcular y añadir tierras básicas para llegar a 60 -----------
    print(f"\n  [3/3] Calculando tierras basicas...\n")

    TIERRA_POR_ARQUETIPO = {
        "descarte": "Swamp",
        "aggro_negro": "Swamp",
        "burn": "Mountain",
        "control_azul": "Island",
        "stompy_verde": "Forest",
    }
    color_tierra = TIERRA_POR_ARQUETIPO.get(arquetipo_key, "Swamp")

    # Contar lo que ya tenemos
    total_hechizos_actual = sum(c["copias"] for c in deck_cartas if not c["es_tierra"])
    total_tierras_especiales = sum(c["copias"] for c in deck_cartas if c["es_tierra"])
    tierras_basicas_necesarias = 60 - total_hechizos_actual - total_tierras_especiales

    print(f"  Hechizos en mazo   : {total_hechizos_actual}")
    print(f"  Tierras especiales : {total_tierras_especiales}")
    print(f"  Tierras basicas    : {max(0, tierras_basicas_necesarias)}")

    if tierras_basicas_necesarias > 0:
        # Buscar la tierra básica en la era con una sola request
        q_tierra = f't:"{color_tierra}" is:basicland {era["filtro_scryfall"]}'
        resultado_tierra = _scryfall_search(q_tierra, max_results=1)

        if resultado_tierra:
            t = resultado_tierra[0]
            set_code = t.get("set", "???").upper()
            col_num = t.get("collector_number", "")
            deck_cartas.append({
                "nombre": color_tierra,
                "copias": tierras_basicas_necesarias,
                "set_code": set_code,
                "collector_number": col_num,
                "tipo": t.get("type_line", f"Basic Land -- {color_tierra}"),
                "es_tierra": True,
                "mana_cost": "",
                "cmc": 0,
                "seccion": "mainboard",
                "fuente": "scryfall",
            })
            print(f"\n    + {tierras_basicas_necesarias}x {color_tierra} ({set_code})")
        else:
            # Fallback: no es esencial tener el set exacto
            print(f"\n  [!] No se encontraron {color_tierra} en la era. Agrega manualmente.")
    elif tierras_basicas_necesarias < 0:
        # Hay demasiadas cartas: recortar tierras especiales o hechizos de apoyo
        exceso = abs(tierras_basicas_necesarias)
        print(f"\n  [ajuste] Hay {exceso} cartas de más. Recortando...")
        for carta in reversed(deck_cartas):
            if exceso <= 0:
                break
            corte = min(carta["copias"], exceso)
            carta["copias"] -= corte
            exceso -= corte
            if carta["copias"] == 0:
                deck_cartas.remove(carta)
            print(f"    - {corte}x {carta['nombre']}")

    total_final = sum(c["copias"] for c in deck_cartas)
    total_hechizos = sum(c["copias"] for c in deck_cartas if not c["es_tierra"])
    total_tierras_final = sum(c["copias"] for c in deck_cartas if c["es_tierra"])

    return {
        "arquetipo": arquetipo_key,
        "era_key": era_key,
        "era_nombre": era["nombre"],
        "cartas": deck_cartas,
        "total": total_final,
        "total_hechizos": total_hechizos,
        "total_tierras": total_tierras_final,
    }


# --- FORMATEO DE SALIDA -------------------------------------------------------

def a_moxfield(mazo: dict) -> str:
    """Genera lista en formato Moxfield compatible con card_list_parser.py."""
    lineas = []
    lineas.append(f"// Mazo: {mazo['arquetipo'].upper().replace('_', ' ')} -- {mazo['era_nombre']}")
    lineas.append(f"// Generado por MTG Deck Builder")
    lineas.append(f"// Total: {mazo['total']} cartas ({mazo['total_hechizos']} hechizos + {mazo['total_tierras']} tierras)")
    lineas.append("")

    hechizos = [c for c in mazo["cartas"] if not c["es_tierra"]]
    tierras = [c for c in mazo["cartas"] if c["es_tierra"]]

    if hechizos:
        for carta in hechizos:
            set_code = carta.get("set_code", "???")
            col_num = carta.get("collector_number", "1")
            lineas.append(f"{carta['copias']} {carta['nombre']} ({set_code}) {col_num}")

    if tierras:
        lineas.append("")
        for carta in tierras:
            set_code = carta.get("set_code", "???")
            col_num = carta.get("collector_number", "1")
            lineas.append(f"{carta['copias']} {carta['nombre']} ({set_code}) {col_num}")

    return "\n".join(lineas)


def imprimir_resumen(mazo: dict):
    """Imprime resumen del mazo con curva de maná."""
    print(f"\n{'='*60}")
    print(f"  MAZO FINAL -- {mazo['arquetipo'].upper().replace('_',' ')} ({mazo['era_nombre']})")
    print(f"{'='*60}")

    # Curva de maná
    curva = defaultdict(int)
    for carta in mazo["cartas"]:
        if not carta["es_tierra"]:
            cmc = int(carta.get("cmc", 0))
            curva[cmc] += carta["copias"]

    if curva:
        max_count = max(curva.values())
        print("\n  Curva de Maná:")
        for cmc in sorted(curva.keys()):
            count = curva[cmc]
            barra = "█" * int(count * 20 / max_count)
            print(f"  {cmc}: {barra:<20} {count}")

    print(f"\n  Hechizos : {mazo['total_hechizos']}")
    print(f"  Tierras  : {mazo['total_tierras']}")
    print(f"  TOTAL    : {mazo['total']} cartas")

    if mazo["total"] != 60:
        diferencia = 60 - mazo["total"]
        if diferencia > 0:
            print(f"\n  [!] Faltan {diferencia} cartas para completar 60.")
        else:
            print(f"\n  [!] Hay {abs(diferencia)} cartas de más.")


# --- INTERFAZ PRINCIPAL -------------------------------------------------------

def menu_interactivo():
    """Modo interactivo cuando no se dan argumentos."""
    print("\n" + "=" * 60)
    print("   MTG DECK BUILDER -- Old School / Mid School")
    print("   Busqueda via Scryfall API")
    print("=" * 60)

    print("\n  ARQUETIPOS disponibles:")
    arquetipos_lista = list(STAPLES.keys())
    for i, key in enumerate(arquetipos_lista, 1):
        nombre = key.replace("_", " ").title()
        print(f"    [{i}] {key:<20} → {nombre}")

    print("\n  ERAS disponibles:")
    eras_lista = list(ERAS.keys())
    for i, key in enumerate(eras_lista, 1):
        print(f"    [{i}] {key:<15} → {ERAS[key]['nombre']}")
        print(f"        {ERAS[key]['descripcion'][:56]}...")

    print()
    while True:
        entrada = input("  Arquetipo (nombre o número): ").strip().lower()
        if entrada.isdigit() and 1 <= int(entrada) <= len(arquetipos_lista):
            arquetipo_key = arquetipos_lista[int(entrada) - 1]
            break
        if entrada in STAPLES:
            arquetipo_key = entrada
            break
        print(f"  [!] Opción inválida. Elige entre: {', '.join(arquetipos_lista)}")

    while True:
        entrada = input("  Era (nombre o número) [old_school]: ").strip().lower() or "old_school"
        if entrada.isdigit() and 1 <= int(entrada) <= len(eras_lista):
            era_key = eras_lista[int(entrada) - 1]
            break
        if entrada in ERAS:
            era_key = entrada
            break
        print(f"  [!] Opción inválida. Elige entre: {', '.join(eras_lista)}")

    salida = input("  Archivo de salida [Enter = mostrar en pantalla]: ").strip() or None
    return arquetipo_key, era_key, salida


def main():
    parser = argparse.ArgumentParser(
        description="MTG Deck Builder -- Old School / Mid School",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Arquetipos: {', '.join(STAPLES.keys())}
Eras:       {', '.join(ERAS.keys())}

Ejemplos:
  python deck_builder.py -a descarte -e old_school -o mazo_descarte.txt
  python deck_builder.py -a burn -e mid_school
  python deck_builder.py -a control_azul -e ambos --formato json
        """,
    )
    parser.add_argument("-a", "--arquetipo", choices=list(STAPLES.keys()), help="Arquetipo del mazo")
    parser.add_argument("-e", "--era", choices=list(ERAS.keys()), default="old_school", help="Era de cartas")
    parser.add_argument("-o", "--output", help="Archivo de salida (.txt)")
    parser.add_argument("--formato", choices=["moxfield", "json"], default="moxfield", help="Formato de salida")
    parser.add_argument("--lista-arquetipos", action="store_true", help="Listar arquetipos disponibles")
    parser.add_argument("--fabricar", "-f", action="store_true",
                        help="Fabricar cartas automáticamente con make_cards_old_border.py tras guardar")
    args = parser.parse_args()

    if args.lista_arquetipos:
        print("\nArquetipos disponibles:")
        for key in STAPLES:
            print(f"  {key}")
        print("\nEras disponibles:")
        for key, era in ERAS.items():
            print(f"  {key}: {era['nombre']}")
        return

    # Modo interactivo si no se pasaron argumentos
    if not args.arquetipo:
        arquetipo_key, era_key, salida_path = menu_interactivo()
    else:
        arquetipo_key = args.arquetipo
        era_key = args.era
        salida_path = args.output

    # Construir el mazo
    mazo = construir_mazo(arquetipo_key, era_key)

    # Mostrar resumen
    imprimir_resumen(mazo)

    # Formatear salida
    if args.formato == "json":
        contenido = json.dumps(mazo, indent=2, ensure_ascii=False)
        ext = ".json"
    else:
        contenido = a_moxfield(mazo)
        ext = ".txt"

    # Determinar nombre de archivo si no se especificó
    if not salida_path and args.arquetipo:
        salida_path = os.path.join(
            os.path.dirname(__file__), "data",
            f"mazo_{arquetipo_key}_{era_key}{ext}"
        )

    if salida_path:
        os.makedirs(os.path.dirname(os.path.abspath(salida_path)), exist_ok=True)
        with open(salida_path, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"\n  Lista guardada: {salida_path}")

        if args.fabricar and ext == ".txt":
            fabricador = os.path.join(os.path.dirname(__file__), "make_cards_old_border.py")
            print(f"\n[*] Fabricando cartas con make_cards_old_border.py...")
            subprocess.run([sys.executable, fabricador, "--input", salida_path], check=True)
        else:
            print(f"\n  Siguiente paso:")
            print(f"    python make_cards_old_border.py --input \"{salida_path}\"")
    else:
        print(f"\n{'='*60}")
        print("  LISTA MOXFIELD:")
        print("=" * 60)
        print(contenido)
        print(f"\n  Copia esta lista y úsala con make_cards_old_border.py")


if __name__ == "__main__":
    main()
