#!/usr/bin/env python3
"""Check consistency between Logos gate and 100pct closure artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs/final/artifacts/logos_rag_btrack_promotion_gate_v1_latest.json"
DEFAULT_CLOSURE = ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_gate_closure_consistency_v1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--closure-json", type=Path, default=DEFAULT_CLOSURE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _read_json(args.gate_json)
    closure = _read_json(args.closure_json)

    gate_l2 = bool((((gate.get("tiers") or {}).get("L2_track_c_shadow_ingest") or {}).get("passed")))
    gate_hit3 = float((gate.get("metrics") or {}).get("weak_gold_hit_at_3") or 0.0)
    gate_bridge_n = int(((gate.get("metrics") or {}).get("bridge_rag_evidence_n") or 0))

    closure_sem = ((closure.get("checks") or {}).get("semantic_rag_quality") or {})
    closure_l2 = bool(closure_sem.get("L2_passed"))
    closure_hit3 = float(closure_sem.get("weak_gold_hit_at_3") or 0.0)
    closure_ok = bool(closure.get("closure_ok"))

    checks = {
        "gate_l2_equals_closure_l2": gate_l2 == closure_l2,
        "weak_hit3_equal_rounded_6dp": round(gate_hit3, 6) == round(closure_hit3, 6),
        "gate_bridge_evidence_min_20": gate_bridge_n >= 20,
        "closure_ok_true": closure_ok,
    }
    ok = all(checks.values())

    out_doc = {
        "schema": "logos_gate_closure_consistency_v1",
        "ok": ok,
        "gate_l2_passed": gate_l2,
        "closure_l2_passed": closure_l2,
        "gate_weak_gold_hit_at_3": gate_hit3,
        "closure_weak_gold_hit_at_3": closure_hit3,
        "gate_bridge_rag_evidence_n": gate_bridge_n,
        "closure_ok": closure_ok,
        "checks": checks,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
