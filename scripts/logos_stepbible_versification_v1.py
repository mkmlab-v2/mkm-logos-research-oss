"""Parse STEPBible TVTMS versification (sparse checkout) → MT verse_id candidates for WLC/SBLGNT."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TVTMS = (
    ROOT
    / "vault/external_lexicon/sources/stepbible-data/Versification"
    / "TVTMS - Translators Versification Traditions with Methodology for Standardisation for Eng+Heb+Lat+Grk+Others - STEPBible.org CC BY.txt"
)

BOOK_TO_CANON: dict[str, str] = {
    "Gen": "Gen",
    "Exo": "Exod",
    "Lev": "Lev",
    "Num": "Num",
    "Deu": "Deut",
    "Jos": "Josh",
    "Jdg": "Judg",
    "Rut": "Ruth",
    "1Sa": "1Sam",
    "2Sa": "2Sam",
    "1Ki": "1Kgs",
    "2Ki": "2Kgs",
    "1Ch": "1Chr",
    "2Ch": "2Chr",
    "Ezr": "Ezra",
    "Neh": "Neh",
    "Est": "Esth",
    "Job": "Job",
    "Psa": "Ps",
    "Pro": "Prov",
    "Ecc": "Eccl",
    "Sng": "Song",
    "Isa": "Isa",
    "Jer": "Jer",
    "Lam": "Lam",
    "Eze": "Ezek",
    "Dan": "Dan",
    "Hos": "Hos",
    "Jol": "Joel",
    "Amo": "Amos",
    "Oba": "Obad",
    "Jon": "Jonah",
    "Mic": "Mic",
    "Nam": "Nah",
    "Hab": "Hab",
    "Zep": "Zeph",
    "Hag": "Hag",
    "Zec": "Zech",
    "Mal": "Mal",
    "Mat": "Matt",
    "Mrk": "Mark",
    "Luk": "Luke",
    "Jhn": "Jhn",
    "Act": "Acts",
    "Rom": "Rom",
    "1Co": "1Cor",
    "2Co": "2Cor",
    "Gal": "Gal",
    "Eph": "Eph",
    "Php": "Phil",
    "Col": "Col",
    "1Th": "1Thess",
    "2Th": "2Thess",
    "1Ti": "1Tim",
    "2Ti": "2Tim",
    "Tit": "Titus",
    "Phm": "Phlm",
    "Heb": "Heb",
    "Jas": "Jas",
    "1Pe": "1Pet",
    "2Pe": "2Pet",
    "1Jn": "1John",
    "2Jn": "2John",
    "3Jn": "3John",
    "Jud": "Jude",
    "Rev": "Rev",
}

_REF_RE = re.compile(r"^([A-Za-z0-9]+)\.(\d+):(\d+)(?:-(\d+))?$")
_JSWORD_MAP_RE = re.compile(r"([A-Za-z0-9.]+!?\w*)=([A-Za-z0-9.]+!?\w*)")


def _canon_book(step: str) -> str:
    base = step.split(".")[0]
    return BOOK_TO_CANON.get(base, base)


def _parse_ref(ref: str) -> tuple[str, int, int] | None:
    ref = ref.strip().split()[0]
    m = _REF_RE.match(ref)
    if not m:
        return None
    book, ch, v1, v2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    return _canon_book(book), ch, int(v2) if v2 else v1


def _verse_id(book: str, ch: int, v: int) -> str:
    return f"{book}.{ch}.{v}"


def _expand_side(ref: str) -> list[tuple[str, int, int]]:
    ref = ref.strip()
    if not ref or ref.lower().startswith("absent"):
        return []
    m = _REF_RE.match(ref.split()[0])
    if not m:
        return []
    book = _canon_book(m.group(1))
    ch = int(m.group(2))
    v1 = int(m.group(3))
    v2 = int(m.group(4)) if m.group(4) else v1
    return [(book, ch, v) for v in range(v1, v2 + 1)]


def _pair_expand(eng_ref: str, target_ref: str) -> list[tuple[str, str]]:
    el = _expand_side(eng_ref)
    tl = _expand_side(target_ref)
    if not el or not tl:
        return []
    if len(el) == 1 and len(tl) == 1:
        return [(_verse_id(*el[0]), _verse_id(*tl[0]))]
    if len(el) != len(tl):
        return []
    return [(_verse_id(*e), _verse_id(*t)) for e, t in zip(el, tl)]


def _parse_jsword_mapping_line(line: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for lhs, rhs in _JSWORD_MAP_RE.findall(line):
        lhs = lhs.split("!")[0]
        rhs = rhs.split("!")[0]
        lp = _parse_ref(lhs.replace("2Cor", "2Co").replace("Matt", "Mat"))
        rp = _parse_ref(rhs.replace("2Cor", "2Co").replace("Matt", "Mat"))
        if lp and rp:
            out.append((_verse_id(*lp), _verse_id(*rp)))
    return out


def load_stepbible_eng_to_hebrew(path: Path = DEFAULT_TVTMS) -> dict[str, str]:
    """MT-style English verse_id → Hebrew WLC osisID candidate."""
    if not path.is_file():
        return {}
    mapping: dict[str, str] = {}
    hebrew_col = 2
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.startswith("$") and "English KJV" in line:
            parts = line.split("\t")
            try:
                hebrew_col = parts.index("Hebrew")
            except ValueError:
                hebrew_col = 2
            continue
        if not line.startswith("OneToOne\t"):
            continue
        parts = line.split("\t")
        if len(parts) <= hebrew_col:
            continue
        for eng, heb in _pair_expand(parts[1], parts[hebrew_col]):
            mapping[eng] = heb
    return mapping


def load_stepbible_eng_to_greek(path: Path = DEFAULT_TVTMS) -> dict[str, str]:
    """MT-style English verse_id → SBLGNT-style verse_id candidate."""
    if not path.is_file():
        return {}
    mapping: dict[str, str] = {}
    greek_col = 2
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.startswith("$") and "English KJV" in line:
            parts = line.split("\t")
            greek_col = 2
            for label in ("Greek+NRSV", "Greek", "Greek2"):
                if label in parts:
                    greek_col = parts.index(label)
                    break
            continue
        if line.startswith("OneToOne\t"):
            parts = line.split("\t")
            if len(parts) <= greek_col:
                continue
            for eng, grk in _pair_expand(parts[1], parts[greek_col]):
                if grk.lower().startswith("absent"):
                    continue
                mapping[eng] = grk
            continue
        if "2Cor.13" in line or "jsword_mappings" in line:
            for eng, grk in _parse_jsword_mapping_line(line):
                mapping[eng] = grk
    # Explicit KJV colophon / numbering rows from NT table
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if "\t2Co.13:14\t" in line and "2Cor.13.13=2Cor.13.14" in line:
            mapping["2Cor.13.14"] = "2Cor.13.13"
    return mapping


def stepbible_sblgnt_candidates_for_mt_verse(
    verse_id: str,
    *,
    hebrew_map: dict[str, str] | None = None,
    greek_map: dict[str, str] | None = None,
) -> list[str]:
    """Ordered SBLGNT verse_id candidates (STEPBible Greek + Hebrew-column NT merges)."""
    if hebrew_map is None:
        hebrew_map = load_stepbible_eng_to_hebrew()
    if greek_map is None:
        greek_map = load_stepbible_eng_to_greek()
    out: list[str] = []
    for hit in (greek_map.get(verse_id), hebrew_map.get(verse_id)):
        if hit and hit not in out:
            out.append(hit)
    return out


def stepbible_candidates_for_mt_verse(
    verse_id: str,
    *,
    hebrew_map: dict[str, str] | None = None,
    greek_map: dict[str, str] | None = None,
) -> list[str]:
    return stepbible_sblgnt_candidates_for_mt_verse(
        verse_id, hebrew_map=hebrew_map, greek_map=greek_map
    )
