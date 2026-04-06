"""Regression: wide.json / wide_restored.json reproducible from verse report + geumhwa formula."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSE_REPORT = ROOT / "data" / "logos" / "reports" / "logos_report_gen1_john1_wide_20260314.json"
WIDE = ROOT / "data" / "logos" / "reports" / "wide.json"
WIDE_RESTORED = ROOT / "data" / "logos" / "reports" / "wide_restored.json"


def _row_close(a: dict, b: dict) -> bool:
    if set(a.keys()) != set(b.keys()):
        return False
    for k in a:
        if k == "corrected_vector_4d":
            ca, cb = a[k], b[k]
            if not all(
                math.isclose(ca[ax], cb[ax], rel_tol=1e-15, abs_tol=1e-12)
                for ax in ("S", "L", "K", "M")
            ):
                return False
        elif isinstance(a[k], float):
            if not math.isclose(a[k], b[k], rel_tol=1e-15, abs_tol=1e-15):
                return False
        elif a[k] != b[k]:
            return False
    return True


def test_build_matches_committed_artifacts() -> None:
    from scripts.build_logos_wide_restoration import build_wide_rows, filter_wide20

    doc = json.loads(VERSE_REPORT.read_text(encoding="utf-8"))
    verse_level = doc["verse_level"]
    wide_rows = build_wide_rows(verse_level)
    verse_by_id = {str(v["verse_id"]): v for v in verse_level}
    wide20 = filter_wide20(wide_rows, verse_by_id, 0.156, 0.20)

    gw = json.loads(WIDE.read_text(encoding="utf-8"))
    gr = json.loads(WIDE_RESTORED.read_text(encoding="utf-8"))

    assert len(wide_rows) == len(gw) == 82
    assert len(wide20) == len(gr) == 20
    for a, b in zip(wide_rows, gw):
        assert _row_close(a, b), a["verse_id"]
    for a, b in zip(wide20, gr):
        assert _row_close(a, b), a["verse_id"]


def test_distance_band_selects_wide20_ids() -> None:
    doc = json.loads(VERSE_REPORT.read_text(encoding="utf-8"))
    sel = [
        v["verse_id"]
        for v in doc["verse_level"]
        if str(v["verse_id"]).startswith(("Gen.1.", "John.1."))
        and 0.156 <= float(v["distance"]) <= 0.20
    ]
    gr = json.loads(WIDE_RESTORED.read_text(encoding="utf-8"))
    assert [r["verse_id"] for r in gr] == sel
