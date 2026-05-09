#!/usr/bin/env python3
"""Build coordinator decision pack from staged fusion artifacts."""

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
    ap.add_argument("--status-json", type=Path, default=ART / "three_lens_staged_inclusion_status_latest.json")
    ap.add_argument("--fusion-json", type=Path, default=ART / "three_lens_fusion_coordinator_v1_latest.json")
    ap.add_argument("--gate-json", type=Path, default=ART / "three_lens_feature_gate_v2_latest.json")
    ap.add_argument("--external-intel-json", type=Path, default=ART / "three_lens_external_intel_snapshot_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "three_lens_coordinator_decision_pack_v1_latest.json")
    args = ap.parse_args()

    status_path = args.status_json if args.status_json.is_absolute() else ROOT / args.status_json
    fusion_path = args.fusion_json if args.fusion_json.is_absolute() else ROOT / args.fusion_json
    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    external_intel_path = args.external_intel_json if args.external_intel_json.is_absolute() else ROOT / args.external_intel_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    status = _read_json(status_path)
    fusion = _read_json(fusion_path)
    gate = _read_json(gate_path)
    external_intel = _read_json(external_intel_path) if external_intel_path.is_file() else {}

    vec = ((fusion.get("fusion") or {}).get("common_feature_vector_v1") or {})
    metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
    decision = gate.get("decision") if isinstance(gate.get("decision"), dict) else {}
    action = str(decision.get("action") or "WATCH").upper()
    source_action = str(metrics.get("source_action") or "WATCH").upper()
    conflict_list = ((fusion.get("fusion") or {}).get("conflicts") or [])

    top_evidence = [
        str(fusion.get("inputs", {}).get("sasang_json") or ""),
        str(fusion.get("inputs", {}).get("myeongni_json") or ""),
        str(fusion.get("inputs", {}).get("logos_json") or ""),
    ]
    for p in vec.get("chronicle_evidence_pointers") or []:
        top_evidence.append(str(p))
    top_evidence = [x for x in top_evidence if x][:5]

    payload = {
        "schema": "three_lens_coordinator_decision_pack_v1",
        "generated_at_utc": _now(),
        "final_decision": {
            "action": action,
            "reason": str(decision.get("reason") or "n/a"),
            "source_action": source_action,
            "human_signoff_required": True,
            "research_only": True,
        },
        "scores": {
            "risk_score_0_1": float(metrics.get("risk_score_0_1") or 0.0),
            "opportunity_score_0_1": float(metrics.get("opportunity_score_0_1") or 0.0),
        },
        "conflict_resolution_log": {
            "conflict_count": len(conflict_list),
            "conflicts": conflict_list,
            "status_hint": str(status.get("decision_hint") or "WATCH"),
        },
        "top_evidence_paths": top_evidence,
        "external_intel_context": {
            "input_json": str(external_intel_path),
            "ready_for_orchestrator_context": bool(external_intel.get("ready_for_orchestrator_context")),
            "freshness": external_intel.get("freshness"),
            "external_macro": external_intel.get("external_macro"),
            "external_news": external_intel.get("external_news"),
            "lens_scores": external_intel.get("lens_scores"),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
