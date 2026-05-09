#!/usr/bin/env python3
"""Build evidence trace for three-lens coordinator outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fusion-json", type=Path, default=ART / "three_lens_fusion_coordinator_v1_latest.json")
    ap.add_argument("--gate-json", type=Path, default=ART / "three_lens_feature_gate_v2_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "three_lens_evidence_trace_v1_latest.json")
    args = ap.parse_args()

    fusion = _read_json(args.fusion_json if args.fusion_json.is_absolute() else ROOT / args.fusion_json)
    gate = _read_json(args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json)

    vec = ((fusion.get("fusion") or {}).get("common_feature_vector_v1") or {})
    metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
    contrib = [
        {"feature": "sasang_stress_score_0_1", "value": float(vec.get("sasang_stress_score_0_1") or 0.0), "weight": 0.45, "used_in": "risk_score"},
        {"feature": "logos_tension_score_0_1", "value": float(vec.get("logos_tension_score_0_1") or 0.0), "weight": 0.35, "used_in": "risk_score"},
        {"feature": "myeongni_confidence_score_0_1", "value": float(vec.get("myeongni_confidence_score_0_1") or 0.0), "weight": 0.20, "used_in": "risk_score_inverse"},
        {"feature": "myeongni_direction_score_0_1", "value": float(vec.get("myeongni_direction_score_0_1") or 0.0), "weight": 0.60, "used_in": "opportunity_score"},
        {"feature": "chronicle_signal_score_0_1", "value": float(vec.get("chronicle_signal_score_0_1") or 0.0), "weight": 0.40, "used_in": "opportunity_score"},
    ]

    payload = {
        "schema": "three_lens_evidence_trace_v1",
        "generated_at_utc": _now(),
        "decision": (gate.get("decision") or {}).get("action", "WATCH"),
        "decision_reason": (gate.get("decision") or {}).get("reason", "n/a"),
        "scores": {
            "risk_score_0_1": float(metrics.get("risk_score_0_1") or 0.0),
            "opportunity_score_0_1": float(metrics.get("opportunity_score_0_1") or 0.0),
        },
        "contributions": contrib,
        "chronicle_evidence_pointers": vec.get("chronicle_evidence_pointers") if isinstance(vec.get("chronicle_evidence_pointers"), list) else [],
        "inputs": fusion.get("inputs") if isinstance(fusion.get("inputs"), dict) else {},
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
