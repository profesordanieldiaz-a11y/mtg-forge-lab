"""
card_list_parser.py
Parsea listas de cartas MTG en los formatos: Moxfield, Arena, MTGO y Plain Text.

Retorna una lista normalizada de entradas:
    {
        "name": str,
        "count": int,
        "set_code": str | None,
        "collector_number": str | None,
        "foil": bool,
        "section": "mainboard" | "sideboard"
    }
"""

import re
from typing import List, Optional

# ─── Patrones ────────────────────────────────────────────────────────────────

# Moxfield / Arena: "2 Card Name (SET) 123" o "2 Card Name (SET) 123 *F*"
_RE_MOXFIELD = re.compile(
    r"^(\d+)\s+(.+?)\s+\(([A-Z0-9]+)\)\s+([\w★]+p?)\s*(\*F\*)?$",
    re.IGNORECASE | re.MULTILINE,
)

# MTGO con set entre corchetes: "2 Card Name [SET]"
_RE_MTGO_SET = re.compile(
    r"^(\d+)\s+(.+?)\s+\[([A-Z0-9]+)\]\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Plain text / MTGO sin set: "2 Card Name"
_RE_PLAIN = re.compile(r"^(\d+)\s+(.+)$", re.MULTILINE)

# Cabeceras de sección
_SECTION_HEADERS = {
    "sideboard", "sb", "maybeboard", "maybe",
    "deck", "mainboard", "main",
}
_RE_SIDEBOARD = re.compile(
    r"^(sideboard|sb|side\s*board)[:\s]*$", re.IGNORECASE
)
_RE_MAINBOARD = re.compile(
    r"^(deck|mainboard|main)[:\s]*$", re.IGNORECASE
)


# ─── Detección de formato ────────────────────────────────────────────────────

def detect_format(text: str) -> str:
    """Devuelve 'moxfield', 'arena', 'mtgo' o 'plain'."""
    has_paren_set    = bool(_RE_MOXFIELD.search(text))
    has_bracket_set  = bool(_RE_MTGO_SET.search(text))
    # "Deck" al inicio de línea es exclusivo de Arena
    has_arena_header = bool(re.search(r"^Deck\s*$", text, re.MULTILINE))

    if has_paren_set and has_arena_header:
        return "arena"
    if has_paren_set:
        return "moxfield"
    if has_bracket_set:
        return "mtgo"
    return "plain"


# ─── Parser principal ────────────────────────────────────────────────────────

def parse_card_list(text: str) -> List[dict]:
    """
    Parsea el texto de una lista de cartas y devuelve entradas normalizadas.
    Detecta automáticamente el formato.
    """
    fmt = detect_format(text)
    print(f"[Parser] Formato detectado: {fmt.upper()}")

    entries = []
    section = "mainboard"

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # Ignorar líneas vacías y comentarios
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        # Detectar cabeceras de sección
        if _RE_SIDEBOARD.match(line):
            section = "sideboard"
            continue
        if _RE_MAINBOARD.match(line):
            section = "mainboard"
            continue
        # Arena separa secciones con línea en blanco después de "Sideboard"
        if line.lower().rstrip(":") in _SECTION_HEADERS:
            section = "sideboard" if "side" in line.lower() or line.lower().rstrip(":") == "sb" else "mainboard"
            continue

        entry = _parse_line(line, fmt, section)
        if entry:
            entries.append(entry)

    print(f"[Parser] {len(entries)} cartas en {fmt.upper()} -> {sum(e['count'] for e in entries)} total con copias")
    return entries


def _parse_line(line: str, fmt: str, section: str) -> Optional[dict]:
    """Intenta parsear una línea según el formato detectado."""

    # Intentar Moxfield/Arena primero (más específico)
    m = _RE_MOXFIELD.match(line)
    if m:
        return {
            "name":             _clean_name(m.group(2)),
            "count":            int(m.group(1)),
            "set_code":         m.group(3).upper(),
            "collector_number": m.group(4),
            "foil":             bool(m.group(5)),
            "section":          section,
        }

    # Intentar MTGO con corchetes
    m = _RE_MTGO_SET.match(line)
    if m:
        return {
            "name":             _clean_name(m.group(2)),
            "count":            int(m.group(1)),
            "set_code":         m.group(3).upper(),
            "collector_number": None,
            "foil":             False,
            "section":          section,
        }

    # Plain text: solo cantidad + nombre
    m = _RE_PLAIN.match(line)
    if m:
        name = _clean_name(m.group(2))
        if name:
            return {
                "name":             name,
                "count":            int(m.group(1)),
                "set_code":         None,
                "collector_number": None,
                "foil":             False,
                "section":          section,
            }

    return None


def _clean_name(raw: str) -> str:
    """Limpia artefactos del nombre: ★, *F*, espacios extra."""
    name = raw.strip()
    name = re.sub(r"\s*\*F\*\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[★]", "", name)
    return name.strip()


# ─── Carga desde archivo ──────────────────────────────────────────────────────

def load_card_list_file(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return parse_card_list(f.read())


# ─── Carga desde clipboard ────────────────────────────────────────────────────

def load_card_list_clipboard() -> List[dict]:
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return parse_card_list(text)
    except Exception as e:
        raise RuntimeError(f"No se pudo leer el portapapeles: {e}")


# ─── Prueba rápida ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TEST_MOXFIELD = """
2 Allosaurus Shepherd (2X2) 132
2 Beast Within (ONC) 104
4 Castle Garenbrig (PELD) 240p
4 Collected Company (SLD) 166 *F*
2 Door of Destinies (SLD) 1631★ *F*
2 Doubling Season (FDN) 216 *F*

Sideboard
2 Grafdigger's Cage (M20) 227
"""

    TEST_ARENA = """
Deck
4 Lightning Bolt (LEA) 162
2 Counterspell (7ED) 67

Sideboard
2 Tormod's Crypt (CHR) 119
"""

    TEST_MTGO = """
4 Lightning Bolt [LEA]
2 Counterspell [7ED]

SIDEBOARD:
2 Tormod's Crypt [CHR]
"""

    TEST_PLAIN = """
4 Lightning Bolt
2 Counterspell

Sideboard
2 Tormod's Crypt
"""

    for label, txt in [
        ("MOXFIELD", TEST_MOXFIELD),
        ("ARENA",    TEST_ARENA),
        ("MTGO",     TEST_MTGO),
        ("PLAIN",    TEST_PLAIN),
    ]:
        print(f"\n{'='*50}\nTest: {label}")
        entries = parse_card_list(txt)
        for e in entries:
            foil = " [FOIL]" if e["foil"] else ""
            col  = (e["collector_number"] or "").encode("ascii", "replace").decode()
            sset = f" ({e['set_code']} #{col})" if e["set_code"] else ""
            line = f"  {e['count']}x {e['name']}{sset}{foil}  [{e['section']}]"
            print(line.encode("ascii", "replace").decode())
