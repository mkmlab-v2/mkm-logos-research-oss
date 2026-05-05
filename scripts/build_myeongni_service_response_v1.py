#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATES = ROOT / "docs" / "final" / "artifacts" / "myeongni_service_templates_v1.json"
DEFAULT_LENS = ROOT / "reports" / "commander_myeongni_lens_latest.json"
DEFAULT_OUT = ROOT / "reports" / "myeongni_service_response_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_template(templates: dict[str, Any], track: str, intent: str) -> dict[str, Any]:
    t = (templates.get("templates") or {}).get(track) or {}
    if intent not in t:
        raise SystemExit(f"intent not found for {track}: {intent}")
    return t[intent]


def _safe_size_guidance(confidence: float) -> dict[str, Any]:
    # Size-only safety clamp for commander overlay use.
    mul = max(0.1, min(1.0, confidence))
    return {
        "size_multiplier_commander": mul,
        "size_policy": "size_only",
        "direction_override_allowed": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM Myeongni service response payload.")
    ap.add_argument("--track", choices=("track_a", "track_b"), required=True)
    ap.add_argument("--intent", required=True)
    ap.add_argument("--templates-json", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tpl_doc = _read_json(args.templates_json)
    lens = _read_json(args.lens_json) if args.lens_json.is_file() else {}
    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    confidence = float(scores.get("confidence") or 0.5)
    direction = float(scores.get("direction_score") or 0.0)

    selected = _pick_template(tpl_doc, args.track, args.intent)
    policy = (tpl_doc.get("policy") or {}).get(args.track) or {}
    labels = policy.get("labels_required") or []

    if args.track == "track_a":
        decision = "WATCH" if confidence < 0.7 else "GO"
        payload = {
            "schema": "myeongni_service_response_v1",
            "generated_at_utc": _utc_now(),
            "track": "A",
            "intent": selected.get("intent"),
            "labels": labels,
            "field": "decision_assist_runtime",
            "lens": {
                "myeongni_confidence": confidence,
                "myeongni_direction_score_reference_only": direction,
                "logos_mode": "[NON_GATING]",
            },
            "conflict_resolver": {
                "rule": "size_only_priority",
                "direction_override_allowed": False,
            },
            "final_action": {
                "decision": decision,
                "size_guidance": _safe_size_guidance(confidence),
                "invalidate_conditions": [
                    "track wall violation",
                    "manual lock not approved",
                    "schema contract mismatch",
                ],
            },
            "template_contract": selected.get("output_contract"),
        }
    else:
        payload = {
            "schema": "myeongni_service_response_v1",
            "generated_at_utc": _utc_now(),
            "track": "B",
            "intent": selected.get("intent"),
            "labels": labels,
            "field": "wellness_research_runtime",
            "lens": {
                "myeongni_confidence_reference_only": confidence,
                "medical_decision_allowed": False,
            },
            "conflict_resolver": {
                "rule": "non_medical_boundary",
                "diagnosis_allowed": False,
                "prescription_allowed": False,
            },
            "final_action": {
                "decision": "WATCH",
                "medical_boundary_note": "This output is research-only and non-medical.",
                "invalidate_conditions": [
                    "diagnosis claim appears",
                    "prescription claim appears",
                    "clinical guarantee appears",
                ],
            },
            "template_contract": selected.get("output_contract"),
        }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(json.dumps({"track": payload["track"], "intent": payload["intent"], "decision": payload["final_action"]["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
