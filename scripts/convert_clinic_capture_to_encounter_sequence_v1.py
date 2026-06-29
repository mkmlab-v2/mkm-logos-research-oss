#!/usr/bin/env python3
"""Convert clinic_constitution_mvp_capture_v1 → encounter_sequence_v1 [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def convert_capture(capture: dict[str, Any], *, sequence_id: str | None = None) -> dict[str, Any]:
    if capture.get("schema") != "clinic_constitution_mvp_capture_v1":
        raise ValueError("schema must be clinic_constitution_mvp_capture_v1")
    enc = capture.get("encounter") if isinstance(capture.get("encounter"), dict) else {}
    ref_token = str(enc.get("ref_token") or "ENC-UNKNOWN")
    seq_id = sequence_id or f"SEQ-{ref_token.replace('ENC-', '')[:48]}"
    ts = str(capture.get("ts_utc") or _utc())
    ai = capture.get("ai_hypothesis") if isinstance(capture.get("ai_hypothesis"), dict) else {}
    constitution = str(ai.get("constitution") or "uncertain")
    confidence = float(ai.get("confidence") or 0.5)
    proxies = capture.get("observation_proxies") if isinstance(capture.get("observation_proxies"), dict) else {}
    if not proxies:
        proxies = {
            "cold_heat_lean": 0.5,
            "digestion_lean": 0.5,
            "activity_lean": 0.5,
            "moisture_lean": 0.5,
        }

    turn: dict[str, Any] = {
        "turn_index": 0,
        "ts_utc": ts,
        "turn_kind": "initial_survey",
        "modalities_present": capture.get("modalities_present")
        or {"survey": True, "birth_profile": True},
        "observation_proxies": proxies,
        "ai_hypothesis": {
            "constitution": constitution,
            "confidence": confidence,
            "model_id": str(ai.get("model_id") or "clinic_capture_convert_v1"),
            "rationale_short": str(ai.get("rationale_short") or "[HYPO] clinic capture 단일턴 변환"),
        },
    }

    doc: dict[str, Any] = {
        "schema": "encounter_sequence_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "domain_lane": "tkm_korean_han_medicine",
        "sasang_primary": True,
        "boundary_contract": {
            "physician_final_authority": True,
            "ai_hypothesis_reference_only": True,
            "no_prescription_output": True,
            "no_emergency_autodispatch": True,
            "track_a_autobind_forbidden": True,
        },
        "encounter": {"ref_token": ref_token, "sequence_id": seq_id},
        "turns": [turn],
        "sequence_summary": {
            "turn_count": 1,
            "constitution_trajectory": [constitution],
            "confidence_trajectory": [confidence],
            "final_ai_constitution": constitution,
            "final_ai_confidence": confidence,
        },
    }

    phys = capture.get("physician_constitution") if isinstance(capture.get("physician_constitution"), dict) else {}
    agr = capture.get("agreement") if isinstance(capture.get("agreement"), dict) else {}
    if phys and agr:
        doc["physician_closure"] = {
            "ts_utc": ts,
            "physician_constitution": {
                "label": str(phys.get("label") or "withheld"),
                "recorded_by_role": str(phys.get("recorded_by_role") or "licensed_km_physician"),
                "notes": phys.get("notes"),
            },
            "agreement": {
                "ai_physician_match": bool(agr.get("ai_physician_match")),
                "disagreement_code": str(agr.get("disagreement_code") or "none"),
            },
            "clinic_capture_ref": capture.get("intake_ref"),
        }
        if agr.get("ai_physician_match") is False:
            doc["curated_learning_pointer"] = {
                "disagreement_recorded": True,
                "curated_path_status": "pending_human_review",
                "note_ko": "[HYPO] clinic capture 불일치 → human-curated correction; auto-training 금지",
            }

    import importlib.util

    l0_path = ROOT / "scripts/tkm_encounter_sequence_l0_router_v1.py"
    l0_spec = importlib.util.spec_from_file_location("tkm_encounter_sequence_l0_router_v1", l0_path)
    if l0_spec and l0_spec.loader:
        l0_mod = importlib.util.module_from_spec(l0_spec)
        l0_spec.loader.exec_module(l0_mod)
        doc = l0_mod.attach_l0_router(doc, capture=capture)

    sidecar_path = ROOT / "scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py"
    spec = importlib.util.spec_from_file_location("tkm_encounter_sequence_myeongni_sidecar_v1", sidecar_path)
    if spec and spec.loader:
        sidecar_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sidecar_mod)
        sidecar_mod.ensure_stub_report()
        doc = sidecar_mod.attach_sidecar(doc, capture=capture)

    logos_path = ROOT / "scripts/tkm_encounter_sequence_logos_sidecar_v1.py"
    logos_spec = importlib.util.spec_from_file_location("tkm_encounter_sequence_logos_sidecar_v1", logos_path)
    if logos_spec and logos_spec.loader:
        logos_mod = importlib.util.module_from_spec(logos_spec)
        logos_spec.loader.exec_module(logos_mod)
        doc = logos_mod.attach_sidecar(doc, capture=capture)

    resolver_path = ROOT / "scripts/tkm_encounter_sequence_conflict_resolver_v1.py"
    resolver_spec = importlib.util.spec_from_file_location("tkm_encounter_sequence_conflict_resolver_v1", resolver_path)
    if resolver_spec and resolver_spec.loader:
        resolver_mod = importlib.util.module_from_spec(resolver_spec)
        resolver_spec.loader.exec_module(resolver_mod)
        doc = resolver_mod.attach_observation(doc)

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sequence-id", default=None)
    args = ap.parse_args()
    capture = json.loads(args.capture_json.read_text(encoding="utf-8-sig"))
    doc = convert_capture(capture, sequence_id=args.sequence_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "sequence_id": doc["encounter"]["sequence_id"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
