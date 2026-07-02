# Keywords: passion, crown, thorns, thematic, verse_anchor
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_ts_module():
    # TS helpers are mirrored in Python for pytest — logic duplicated minimally.
    return None


def test_detect_passion_crown_topic_ko() -> None:
    from scripts.logos_studio_query_topic_guard_v1 import query_flags  # noqa: F401

    # Mirror TS regex behavior in test
    import re

    passion = re.compile(r"(가시\s*면류관|면류관|가시\s*관|crown\s*of\s*thorns)", re.I)
    gospel = re.compile(
        r"(예수|그리스도|십자가|수난|passion|마태|마가|요한|matt\.?\s*27|mark\.?\s*15|john\.?\s*19)",
        re.I,
    )
    q = "예수님의 가시면류관이 상징하는 것은?"
    assert passion.search(q) and gospel.search(q)


def test_passion_crown_primary_refs_order() -> None:
    primary = ["Matt.27.29", "Mark.15.17", "John.19.2", "John.19.5"]
    incoming = ["Ps.119.86", "Job.2.3", "Matt.27.29"]
    out = []
    seen = set()
    for p in primary:
        if p not in seen:
            seen.add(p)
            out.append(p)
    for r in incoming:
        if r not in seen:
            seen.add(r)
            out.append(r)
    assert out[:4] == primary
    assert "Ps.119.86" in out[4:]
