#!/usr/bin/env python3
"""
Rebuild data/logos/reports/wide.json and wide_restored.json from a Logos Gen1+John1 verse report.

Metrics are structural (restoration_rate, renormalized 4D), not market prediction — see
docs/verified_knowledge_base/unified_field_theory/geumhwa_exchange.json (방법론#12).

Inputs: verse_level rows with verse_id, S, L, K, M, distance.
Wide20 subset: Gen.1.* / John.1.* with distance in [distance_min, distance_max] (default 0.156–0.20).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT

DEFAULT_VERSE_REPORT = (
    REPO / "data" / "logos" / "reports" / "logos_report_gen1_john1_wide_20260314.json"
)
DEFAULT_WIDE = REPO / "data" / "logos" / "reports" / "wide.json"
DEFAULT_WIDE_RESTORED = REPO / "data" / "logos" / "reports" / "wide_restored.json"

EARTH_MEDIATION = 0.9
BASE_RESTORATION = 0.96
CODEBOOK_REF = "방법론#12"


def _corrected_vector_4d(v: Dict[str, Any]) -> Dict[str, float]:
    """
    Legacy wide.json rules:
    - If S+L+K+M sums to 1 within ~1e-9, keep verse-level floats (6-decimal display).
    - Otherwise renormalize with float division (matches geumhwa_exchange wide pipeline).
    """
    raw = {k: float(v[k]) for k in ("S", "L", "K", "M")}
    s = sum(raw.values())
    if s <= 0:
        raise ValueError("S+L+K+M sum must be positive")
    if abs(s - 1.0) < 1e-9:
        return raw.copy()
    return {k: raw[k] / s for k in ("S", "L", "K", "M")}


def _row_from_verse(
    verse: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    vid = str(verse["verse_id"])
    raw_sklm = {k: float(verse[k]) for k in ("S", "L", "K", "M")}
    geumhwa_index = raw_sklm["K"] * (1.0 - raw_sklm["M"]) * EARTH_MEDIATION
    restoration_rate = min(0.9999, BASE_RESTORATION + geumhwa_index * 0.0001)
    correction_factor = 1.0 + geumhwa_index * 0.05
    corrected = _corrected_vector_4d(verse)
    out = {
        "verse_id": vid,
        "restoration_rate": restoration_rate,
        "corrected_vector_4d": corrected,
        "correction_factor": correction_factor,
        "geumhwa_index": geumhwa_index,
        "codebook_ref": CODEBOOK_REF,
        "error": None,
    }
    return vid, out


def build_wide_rows(
    verse_level: List[Dict[str, Any]],
    *,
    chapter_prefixes: Tuple[str, ...] = ("Gen.1.", "John.1."),
) -> List[Dict[str, Any]]:
    """Preserve verse_level order (same as legacy wide.json), not lexicographic verse_id."""
    rows: List[Dict[str, Any]] = []
    for verse in verse_level:
        vid = str(verse["verse_id"])
        if not any(vid.startswith(p) for p in chapter_prefixes):
            continue
        _, row = _row_from_verse(verse)
        rows.append(row)
    return rows


def filter_wide20(
    rows: List[Dict[str, Any]],
    verse_by_id: Dict[str, Dict[str, Any]],
    dmin: float,
    dmax: float,
) -> List[Dict[str, Any]]:
    """Subset of wide rows whose distance is in band; preserve order of `rows`."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        vid = row["verse_id"]
        v = verse_by_id.get(vid)
        if v is None:
            continue
        d = float(v["distance"])
        if dmin <= d <= dmax:
            out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build wide.json / wide_restored.json from Logos Gen1+John1 verse report."
    )
    ap.add_argument(
        "--verse-report",
        type=Path,
        default=DEFAULT_VERSE_REPORT,
        help="Path to logos_report_gen1_john1_wide_*.json",
    )
    ap.add_argument("--write-wide", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--write-wide-restored", type=Path, default=DEFAULT_WIDE_RESTORED)
    ap.add_argument("--distance-min", type=float, default=0.156)
    ap.add_argument("--distance-max", type=float, default=0.20)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; do not write files.",
    )
    args = ap.parse_args()

    path = args.verse_report
    if not path.is_file():
        print(f"Missing verse report: {path}", file=sys.stderr)
        return 2

    doc = json.loads(path.read_text(encoding="utf-8"))
    verse_level = doc.get("verse_level") or []
    if not verse_level:
        print("verse_level empty", file=sys.stderr)
        return 2

    wide_rows = build_wide_rows(verse_level)
    verse_by_id = {str(v["verse_id"]): v for v in verse_level}
    wide20 = filter_wide20(wide_rows, verse_by_id, args.distance_min, args.distance_max)

    if args.dry_run:
        print(f"wide rows: {len(wide_rows)}")
        print(f"wide20 rows: {len(wide20)} (distance {args.distance_min}..{args.distance_max})")
        return 0

    args.write_wide.parent.mkdir(parents=True, exist_ok=True)
    args.write_wide.write_text(
        json.dumps(wide_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.write_wide_restored.parent.mkdir(parents=True, exist_ok=True)
    args.write_wide_restored.write_text(
        json.dumps(wide20, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.write_wide} ({len(wide_rows)} rows)")
    print(f"Wrote {args.write_wide_restored} ({len(wide20)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
