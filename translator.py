"""
translator.py
Traduce textos de cartas MTG al español.

Estrategia:
  1. Scryfall /lang=es → si tiene printed_text oficial, lo usa directo
  2. Google Translate (deep-translator) → para cartas sin versión en español
  3. Post-proceso: corrige terminología MTG oficial en español

Guarda nuevas traducciones en mtg_translations_es.json para no re-traducir.
"""

import re, json, os, time, requests

try:
    from deep_translator import GoogleTranslator
    _GT_AVAILABLE = True
except ImportError:
    _GT_AVAILABLE = False

# ─── Tipos de carta ───────────────────────────────────────────────────────────
_SUPERTYPES = {
    "Legendary": "Legendaria",
    "Basic":     "Básica",
    "Snow":      "Nevada",
    "World":     "Mundial",
    "Token":     "Ficha",
}
_CARD_TYPES = {
    "Creature":    "Criatura",
    "Instant":     "Instantáneo",
    "Sorcery":     "Conjuro",
    "Enchantment": "Encantamiento",
    "Artifact":    "Artefacto",
    "Land":        "Tierra",
    "Planeswalker":"Planeswalker",
    "Battle":      "Batalla",
    "Tribal":      "Tribal",
}
_SUBTYPES = {
    # Criaturas
    "Elf":         "Elfo",     "Elves":      "Elfos",
    "Druid":       "Druida",   "Warrior":    "Guerrero",
    "Scout":       "Explorador","Shaman":    "Chamán",
    "Wizard":      "Mago",     "Cleric":     "Clérigo",
    "Rogue":       "Pícaro",   "Archer":     "Arquero",
    "Knight":      "Caballero","Soldier":    "Soldado",
    "Beast":       "Bestia",   "Dragon":     "Dragón",
    "Elemental":   "Elemental","Spirit":     "Espíritu",
    "Zombie":      "Zombie",   "Vampire":    "Vampiro",
    "Goblin":      "Trasgo",   "Angel":      "Ángel",
    "Demon":       "Demonio",  "Human":      "Humano",
    "Merfolk":     "Tritón",   "Faerie":     "Hada",
    "Horror":      "Horror",   "Bird":       "Pájaro",
    "Cat":         "Felino",   "Wolf":       "Lobo",
    "Werewolf":    "Hombre lobo","Dinosaur": "Dinosaurio",
    "Ally":        "Aliado",   "Artificer":  "Artífice",
    "Assassin":    "Asesino",  "Berserker":  "Berserker",
    "Hydra":       "Hidra",    "Sphinx":     "Esfinge",
    "Treefolk":    "Bosquefolk","Wurm":       "Gusano",
    "Spider":      "Araña",    "Snake":      "Serpiente",
    "Insect":      "Insecto",  "Saproling":  "Saprotling",
    "Fungus":      "Hongo",    "Ooze":       "Légamo",
    "Giant":       "Gigante",  "Dwarf":      "Enano",
    # Tierras
    "Forest":      "Bosque",   "Island":     "Isla",
    "Mountain":    "Montaña",  "Plains":     "Llanura",
    "Swamp":       "Pantano",
    # Encantamientos / Artefactos
    "Aura":        "Aura",     "Equipment":  "Equipo",
    "Saga":        "Saga",     "Vehicle":    "Vehículo",
}

def translate_type_line(type_line: str) -> str:
    """Traduce la línea de tipo con tabla de términos oficiales."""
    if not type_line:
        return ""
    # Separar supertipo + tipo — subespecies
    parts = type_line.split(" — ", 1)
    main  = parts[0]
    sub   = parts[1] if len(parts) > 1 else ""

    for en, es in {**_SUPERTYPES, **_CARD_TYPES}.items():
        main = re.sub(rf"\b{en}\b", es, main)

    if sub:
        for en, es in _SUBTYPES.items():
            sub = re.sub(rf"\b{en}\b", es, sub)
        return f"{main} — {sub}"
    return main


# ─── Correcciones de texto MTG (post-proceso Google Translate) ────────────────
_MTG_FIXES = [
    # Reglas base
    (r"\btarget\b",                   "objetivo",          re.IGNORECASE),
    (r"\bDestroy target\b",           "Destruye el objetivo", re.IGNORECASE),
    (r"\bExile target\b",             "Destierra el objetivo", re.IGNORECASE),
    (r"\bSacrifice\b",                "Sacrifica",         re.IGNORECASE),
    (r"\bsacrifice\b",                "sacrifica",         0),
    (r"\bDraw (\d+|a) card[s]?\b",   lambda m: f"Roba {m.group(1) if m.group(1)!='a' else 'una'} carta{'s' if m.group(1) not in ('a','1') else ''}", re.IGNORECASE),
    (r"\benters the battlefield\b",   "entra al campo de batalla", re.IGNORECASE),
    (r"\bleaves the battlefield\b",   "abandona el campo de batalla", re.IGNORECASE),
    (r"\bput[s]? .* into play\b",    "pone en juego", re.IGNORECASE),
    (r"\buntil end of turn\b",        "hasta el final del turno", re.IGNORECASE),
    (r"\bat the beginning of\b",      "al comienzo de", re.IGNORECASE),
    (r"\byour upkeep\b",              "tu mantenimiento", re.IGNORECASE),
    (r"\byour hand\b",                "tu mano", re.IGNORECASE),
    (r"\byour graveyard\b",           "tu cementerio", re.IGNORECASE),
    (r"\byour library\b",             "tu biblioteca", re.IGNORECASE),
    (r"\bthe graveyard\b",            "el cementerio", re.IGNORECASE),
    (r"\bthe battlefield\b",          "el campo de batalla", re.IGNORECASE),
    (r"\beach player\b",              "cada jugador", re.IGNORECASE),
    (r"\bopponent[s]?\b",             "oponente", re.IGNORECASE),
    (r"\bcreature token\b",           "ficha de criatura", re.IGNORECASE),
    (r"\bcreature tokens\b",          "fichas de criatura", re.IGNORECASE),
    (r"\btoken[s]?\b",                "ficha", re.IGNORECASE),
    (r"\bspell[s]?\b",                "hechizo", re.IGNORECASE),
    (r"\bability\b",                  "habilidad", re.IGNORECASE),
    (r"\bactivated ability\b",        "habilidad activada", re.IGNORECASE),
    (r"\btap\b",                      "gira", re.IGNORECASE),
    (r"\buntap\b",                    "endereza", re.IGNORECASE),
    (r"\bcounters?\b(?! target)",     "contador", re.IGNORECASE),
    (r"\b\+1/\+1 counter[s]?\b",     "contador +1/+1", re.IGNORECASE),
    (r"\b-1/-1 counter[s]?\b",       "contador -1/-1", re.IGNORECASE),
    (r"\bcontroller\b",               "controlador", re.IGNORECASE),
    (r"\bowner\b",                    "propietario", re.IGNORECASE),
    (r"\btrigger[s]?\b",              "desencadena", re.IGNORECASE),
    (r"\bstack\b",                    "pila", re.IGNORECASE),
    (r"\bcombat\b",                   "combate", re.IGNORECASE),
    (r"\battack[s]?\b",               "ataque", re.IGNORECASE),
    (r"\bblock[s]?\b",                "bloqueo", re.IGNORECASE),
    (r"\bdoubling\b",                 "duplicar", re.IGNORECASE),
    # Keywords
    (r"\bHaste\b",                    "Prisa",             0),
    (r"\bTrample\b",                  "Arrolla",           0),
    (r"\bFlying\b",                   "Volar",             0),
    (r"\bVigilance\b",                "Vigilancia",        0),
    (r"\bDeathtouch\b",               "Toque letal",       0),
    (r"\bLifelink\b",                 "Vínculo vital",     0),
    (r"\bFirst strike\b",             "Daño de combate primero", 0),
    (r"\bDouble strike\b",            "Doble daño de combate", 0),
    (r"\bHexproof\b",                 "Protección total",  0),
    (r"\bShroud\b",                   "Velo",              0),
    (r"\bIndestructible\b",           "Indestructible",    0),
    (r"\bReach\b",                    "Alcance",           0),
    (r"\bMenace\b",                   "Amenaza",           0),
    (r"\bFlash\b",                    "Fulgor",            0),
    (r"\bProliferate\b",              "Proliferar",        0),
    (r"\bConvoke\b",                  "Convocar",          0),
    (r"\bDelve\b",                    "Hurgar",            0),
    (r"\bFlashback\b",                "Memoria",           0),
    (r"\bKicker\b",                   "Patada",            0),
    (r"\bForest\b(?!\s*—)",           "Bosque",            0),
]

def _apply_fixes(text: str) -> str:
    for pattern, replacement, flags in _MTG_FIXES:
        if callable(replacement):
            text = re.sub(pattern, replacement, text, flags=flags)
        elif flags:
            text = re.sub(pattern, replacement, text, flags=flags)
        else:
            text = re.sub(pattern, replacement, text)
    return text


# ─── Traducción via Google Translate ─────────────────────────────────────────
def _gt_translate(text: str) -> str:
    if not _GT_AVAILABLE or not text.strip():
        return text
    # Proteger símbolos de maná de la traducción
    symbols = re.findall(r"\{[^}]+\}", text)
    placeholder_map = {}
    safe = text
    for i, sym in enumerate(symbols):
        ph = f"XMANAX{i}X"
        safe = safe.replace(sym, ph, 1)
        placeholder_map[ph] = sym

    try:
        translated = GoogleTranslator(source="en", target="es").translate(safe)
        time.sleep(0.3)   # Rate limit gentil
    except Exception as e:
        print(f"    [!] Google Translate: {e}")
        return text

    # Restaurar símbolos
    for ph, sym in placeholder_map.items():
        translated = translated.replace(ph, sym)

    return _apply_fixes(translated)


# ─── Scryfall en español ──────────────────────────────────────────────────────
def _fetch_scryfall_es(name: str) -> dict | None:
    """Intenta obtener la carta en español desde Scryfall."""
    url = f"https://api.scryfall.com/cards/named?exact={requests.utils.quote(name)}&lang=es"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("printed_text"):   # Tiene versión impresa en español
                return {
                    "name_es":  d.get("printed_name") or name,
                    "type_es":  d.get("printed_type_line") or "",
                    "text_es":  d.get("printed_text") or "",
                }
    except Exception:
        pass
    return None


# ─── Función principal ────────────────────────────────────────────────────────
def translate_card(name: str, oracle_text: str, type_line: str) -> dict:
    """
    Retorna {"name_es", "type_es", "text_es"} para una carta.
    Intenta Scryfall ES primero, luego Google Translate.
    """
    # 1. Intentar Scryfall en español oficial
    scryfall_es = _fetch_scryfall_es(name)
    if scryfall_es:
        return scryfall_es

    # 2. Traducir tipo con tabla fija
    type_es = translate_type_line(type_line)

    # 3. Traducir texto con Google Translate + correcciones
    text_es = _gt_translate(oracle_text) if oracle_text else ""

    return {
        "name_es": name,        # Nombre en inglés si no hay oficial en español
        "type_es": type_es,
        "text_es": text_es,
    }


def translate_and_update_json(cards_to_translate: list[dict],
                               json_path: str) -> dict:
    """
    Traduce una lista de cartas y actualiza el archivo JSON de traducciones.
    cards_to_translate: [{"name", "oracle_text", "type_line", "mana_cost"}, ...]
    Retorna el dict de traducciones actualizado.
    """
    with open(json_path, encoding="utf-8") as f:
        db = json.load(f)

    updated = 0
    for i, card in enumerate(cards_to_translate):
        name = card["name"]
        if name in db and db[name].get("text_es"):
            continue   # Ya traducida

        print(f"  [{i+1}/{len(cards_to_translate)}] Traduciendo: {name}")
        result = translate_card(name, card["oracle_text"], card["type_line"])
        db[name] = {
            "name_es":  result["name_es"],
            "type_es":  result["type_es"],
            "text_es":  result["text_es"],
            "mana_cost": card.get("mana_cost", ""),
        }
        updated += 1

    if updated:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {updated} nueva(s) traduccion(es) guardada(s) en {os.path.basename(json_path)}")

    return db
