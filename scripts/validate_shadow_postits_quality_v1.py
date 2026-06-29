#!/usr/bin/env python3
"""Quality gate (non-blocking) for shadow post-it artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TERM = ROOT / "reports/term_postit_shadow_v2_latest.json"
VERSE = ROOT / "reports/verse_metadata_shadow_v2_latest.json"
OUT_DEFAULT = ROOT / "reports/shadow_postits_quality_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build(*, min_confidence: float, min_rows: int) -> dict[str, Any]:
    t = _load(TERM)
    v = _load(VERSE)
    trows = t.get("rows") or []
    vrows = v.get("rows") or []
    t_conf_ok = sum(1 for r in trows if float(r.get("confidence") or 0) >= min_confidence)
    v_conf_ok = sum(1 for r in vrows if float(r.get("confidence") or 0) >= min_confidence)
    t_ev_ok = sum(1 for r in trows if bool((r.get("evidence") or {}).get("verse_count")))
    v_ev_ok = sum(1 for r in vrows if bool((r.get("evidence") or {}).get("citation_hit_count")))
    gate = {
        "term_rows_min_ok": len(trows) >= min_rows,
        "verse_rows_min_ok": len(vrows) >= min_rows,
        "term_confidence_ok_rate": round(t_conf_ok / len(trows), 6) if trows else 0.0,
        "verse_confidence_ok_rate": round(v_conf_ok / len(vrows), 6) if vrows else 0.0,
        "term_evidence_ok_rate": round(t_ev_ok / len(trows), 6) if trows else 0.0,
        "verse_evidence_ok_rate": round(v_ev_ok / len(vrows), 6) if vrows else 0.0,
    }
    overall_ok = all(
        [
            gate["term_rows_min_ok"],
            gate["verse_rows_min_ok"],
            gate["term_evidence_ok_rate"] >= 0.95 if trows else False,
            gate["verse_evidence_ok_rate"] >= 0.95 if vrows else False,
        ]
    )
    return {
        "schema": "shadow_postits_quality_gate_v1",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {"track_a_bridge": False, "live_trading_bridge": False},
        "inputs": {
            "term_postit": str(TERM.relative_to(ROOT)).replace("\\", "/"),
            "verse_postit": str(VERSE.relative_to(ROOT)).replace("\\", "/"),
            "min_confidence": min_confidence,
            "min_rows": min_rows,
        },
        "summary": {"term_rows": len(trows), "verse_rows": len(vrows), "overall_ok": overall_ok},
        "gate": gate,
        "reproduce": "py scripts/validate_shadow_postits_quality_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-confidence", type=float, default=0.7)
    ap.add_argument("--min-rows", type=int, default=8)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build(min_confidence=max(0.0, min(1.0, args.min_confidence)), min_rows=max(1, args.min_rows))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["summary"]["overall_ok"], "summary": doc["summary"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["summary"]["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
