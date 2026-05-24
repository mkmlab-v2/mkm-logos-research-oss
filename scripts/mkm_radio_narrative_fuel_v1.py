"""O-P31c Zone B — optional science narrative fuel (B-track, non-gating)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.mkm_radio_dialogue_guard_v1 import scan_forbidden

DEFAULT_FUEL = Path("data/radio/narrative_fuel_science_v1.example.json")
REQUIRED_SCHEMA = "narrative_fuel_science_v1"
PERSONA_TAGS = {
    "dj_logos": ["LOGOS", "NON_GATING", "NARRATIVE_FUEL"],
    "mc_myeongni": ["MYEONGNI", "HYPO", "NARRATIVE_FUEL"],
    "dr_sasang": ["SASANG", "HYPO", "NARRATIVE_FUEL"],
}


def load_narrative_fuel(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != REQUIRED_SCHEMA:
        raise ValueError(f"schema_must_be_{REQUIRED_SCHEMA}")
    if doc.get("hypothesis_tier") != "B":
        raise ValueError("hypothesis_tier_must_be_B")
    if doc.get("non_gating") is not True or doc.get("boundary_ack") is not True:
        raise ValueError("non_gating_and_boundary_ack_required")
    lines = doc.get("lines_ko") or {}
    for key in ("dj_logos", "mc_myeongni", "dr_sasang"):
        text = str(lines.get(key) or "").strip()
        if not text:
            raise ValueError(f"lines_ko_missing_{key}")
        hits = scan_forbidden(text)
        if hits:
            raise ValueError(f"lines_ko_forbidden_{key}:{','.join(hits)}")
    return doc


def insert_science_fuel_segment(
    segments: List[Dict[str, Any]],
    fuel: Dict[str, Any],
    factory: Any,
    *,
    insert_after_name: str = "logos_citation_pack",
) -> List[Dict[str, Any]]:
    """Insert 3-line fuel pack after named segment; renumber segment_index."""
    lines = fuel.get("lines_ko") or {}
    nid = str(fuel.get("narrative_id") or "narrative_fuel")
    pack = {
        "segment_name": "science_narrative_fuel_pack",
        "dialogue": [
            factory.line(
                "dj_logos",
                str(lines["dj_logos"]),
                tags=PERSONA_TAGS["dj_logos"],
                evidence=nid,
                dur=45.0,
            ),
            factory.line(
                "mc_myeongni",
                str(lines["mc_myeongni"]),
                tags=PERSONA_TAGS["mc_myeongni"],
                evidence=nid,
                dur=50.0,
            ),
            factory.line(
                "dr_sasang",
                str(lines["dr_sasang"]),
                tags=PERSONA_TAGS["dr_sasang"],
                evidence=nid,
                dur=55.0,
            ),
        ],
    }
    out: List[Dict[str, Any]] = []
    inserted = False
    for seg in segments:
        out.append(seg)
        if not inserted and seg.get("segment_name") == insert_after_name:
            out.append(pack)
            inserted = True
    if not inserted:
        out.append(pack)
    for i, seg in enumerate(out, start=1):
        seg["segment_index"] = i
    return out
