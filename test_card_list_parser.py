"""
Tests para card_list_parser.py — parser de listas MTG (Moxfield/Arena/MTGO/Plain).

Ejecutar con pytest:   python -m pytest test_card_list_parser.py -v
O como script:         python test_card_list_parser.py
"""

from card_list_parser import detect_format, parse_card_list, _clean_name


# ─── Fixtures de texto ────────────────────────────────────────────────────────

MOXFIELD = (
    "2 Allosaurus Shepherd (2X2) 132\n"
    "4 Castle Garenbrig (PELD) 240p\n"
    "4 Collected Company (SLD) 166 *F*\n"
    "2 Door of Destinies (SLD) 1631★ *F*\n"
)

ARENA = "Deck\n4 Lightning Bolt (LEA) 162\n\nSideboard\n2 Tormod's Crypt (CHR) 119\n"

MTGO = "4 Lightning Bolt [LEA]\n2 Counterspell [7ED]\n"

PLAIN = "4 Lightning Bolt\n2 Counterspell\n"


# ─── detect_format ────────────────────────────────────────────────────────────

def test_detect_moxfield():
    assert detect_format(MOXFIELD) == "moxfield"

def test_detect_arena():
    # "Deck" header + set en paréntesis => arena (no moxfield)
    assert detect_format(ARENA) == "arena"

def test_detect_mtgo():
    assert detect_format(MTGO) == "mtgo"

def test_detect_plain():
    assert detect_format(PLAIN) == "plain"


# ─── parse_card_list: Moxfield ────────────────────────────────────────────────

def test_moxfield_basic_fields():
    e = parse_card_list(MOXFIELD)[0]
    assert e["name"] == "Allosaurus Shepherd"
    assert e["count"] == 2
    assert e["set_code"] == "2X2"
    assert e["collector_number"] == "132"
    assert e["foil"] is False
    assert e["section"] == "mainboard"

def test_moxfield_collector_with_p_suffix():
    # "240p" no debe perder la 'p'
    castle = [e for e in parse_card_list(MOXFIELD) if e["name"] == "Castle Garenbrig"][0]
    assert castle["collector_number"] == "240p"

def test_moxfield_foil_flag():
    cc = [e for e in parse_card_list(MOXFIELD) if e["name"] == "Collected Company"][0]
    assert cc["foil"] is True

def test_moxfield_star_in_collector_and_clean_name():
    door = [e for e in parse_card_list(MOXFIELD) if e["name"].startswith("Door")][0]
    assert door["name"] == "Door of Destinies"   # sin ★ ni *F*
    assert door["foil"] is True
    assert "★" in door["collector_number"]   # el ★ se conserva en el nº de coleccionista


# ─── parse_card_list: otros formatos ──────────────────────────────────────────

def test_mtgo_brackets():
    e = parse_card_list(MTGO)[0]
    assert (e["name"], e["count"], e["set_code"], e["collector_number"]) == \
           ("Lightning Bolt", 4, "LEA", None)

def test_plain_no_set():
    e = parse_card_list(PLAIN)[0]
    assert e["name"] == "Lightning Bolt"
    assert e["set_code"] is None
    assert e["foil"] is False


# ─── Secciones y limpieza ─────────────────────────────────────────────────────

def test_sideboard_section_detected():
    entries = parse_card_list(ARENA)
    main = [e for e in entries if e["section"] == "mainboard"]
    side = [e for e in entries if e["section"] == "sideboard"]
    assert any(e["name"] == "Lightning Bolt" for e in main)
    assert any(e["name"] == "Tormod's Crypt" for e in side)

def test_comments_and_blank_lines_ignored():
    txt = "// comentario\n# otro\n\n4 Lightning Bolt\n"
    entries = parse_card_list(txt)
    assert len(entries) == 1 and entries[0]["name"] == "Lightning Bolt"

def test_total_copies_count():
    # 2+4+4+2 = 12 copias en 4 entradas
    entries = parse_card_list(MOXFIELD)
    assert len(entries) == 4
    assert sum(e["count"] for e in entries) == 12

def test_clean_name_helper():
    assert _clean_name("Collected Company *F*") == "Collected Company"
    assert _clean_name("Door of Destinies★") == "Door of Destinies"


# ─── Runner standalone (sin pytest) ───────────────────────────────────────────

if __name__ == "__main__":
    import sys
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ok  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERR   {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed de {len(tests)} tests")
    sys.exit(1 if failed else 0)
