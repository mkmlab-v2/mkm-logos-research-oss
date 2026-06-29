#!/usr/bin/env python3
"""Build 41k term post-it shadow v2 from lexicon 4D + verse shadow evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "reports/logos_lexicon_4d_v1_latest.json"
VERSE_SHADOW = ROOT / "reports/verse_metadata_shadow_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/term_postit_shadow_v2_latest.json"

_AXES = ("S", "L", "K", "M")
_KO = {"S": "태양", "L": "소양", "K": "태음", "M": "소음"}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _dist(vec: dict[str, float]) -> dict[str, float]:
    vals = {k: max(1e-9, float(vec.get(k, 0.0))) for k in _AXES}
    s = sum(vals.values()) or 1.0
    return {k: round(vals[k] / s, 6) for k in _AXES}


def build(*, min_verse_count: int, max_rows: int) -> dict[str, Any]:
    lex = _load(LEXICON)
    vshadow = _load(VERSE_SHADOW)
    rows = []
    for r in (lex.get("rows") or []):
        vc = int(r.get("verse_count") or 0)
        if vc < min_verse_count:
            continue
        vec = r.get("vector_4d") or {}
        if not isinstance(vec, dict):
            continue
        d = _dist(vec)
        axis = max(_AXES, key=lambda k: d[k])
        confidence = round(min(0.99, max(0.5, d[axis] + (d[axis] - sorted(d.values(), reverse=True)[1]))), 4)
        rows.append(
            {
                "atom_id": r.get("atom_id"),
                "normalized_form": r.get("normalized_form"),
                "lang": r.get("lang"),
                "role_distribution": {"태양": d["S"], "소양": d["L"], "태음": d["K"], "소음": d["M"]},
                "primary_role": _KO[axis],
                "weight": round(float(d[axis]), 6),
                "confidence": confidence,
                "evidence": {
                    "verse_count": vc,
                    "token_occurrences": int(r.get("token_occurrences") or 0),
                    "source": "lexicon_4d_v1",
                },
                "non_gating": True,
                "research_only": True,
            }
        )
        if max_rows and len(rows) >= max_rows:
            break
    return {
        "schema": "term_postit_shadow_v2",
        "version": "2.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "ms_headline_merge_forbidden": True,
        },
        "inputs": {
            "lexicon_4d": str(LEXICON.relative_to(ROOT)).replace("\\", "/"),
            "verse_shadow": str(VERSE_SHADOW.relative_to(ROOT)).replace("\\", "/"),
            "min_verse_count": min_verse_count,
            "max_rows": max_rows,
        },
        "summary": {
            "rows": len(rows),
            "verse_shadow_rows": int((vshadow.get("summary") or {}).get("shadow_rows") or 0),
        },
        "rows": rows,
        "reproduce": "py scripts/build_41k_postit_shadow_v2.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-verse-count", type=int, default=3)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build(min_verse_count=max(1, args.min_verse_count), max_rows=max(0, args.max_rows))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = int((doc.get("summary") or {}).get("rows") or 0) > 0
    print(json.dumps({"ok": ok, "rows": doc["summary"]["rows"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
