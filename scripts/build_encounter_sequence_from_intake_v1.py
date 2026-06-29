#!/usr/bin/env python3
"""Build encounter_sequence_v1 from patient intake fusion JSON [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

LABEL_MAP = {
    "태음": "taeeum",
    "태음인": "taeeum",
    "taeeum": "taeeum",
    "소양": "soyang",
    "소양인": "soyang",
    "soyang": "soyang",
    "태양": "taeyang",
    "태양인": "taeyang",
    "taeyang": "taeyang",
    "소음": "soeum",
    "소음인": "soeum",
    "soeum": "soeum",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _constitution_from_label(label: str) -> str:
    s = (label or "").strip().lower()
    for key, val in LABEL_MAP.items():
        if key.lower() in s or s == val:
            return val
    return "uncertain"


def _intake_text_blob(intake_doc: dict[str, Any]) -> str:
    intake = intake_doc.get("intake") if isinstance(intake_doc.get("intake"), dict) else {}
    parts: list[str] = []
    for sym in intake.get("symptoms") or []:
        parts.append(str(sym))
    for key in ("situation", "subjective_notes", "objective_draft"):
        parts.append(str(intake.get(key) or ""))
    return " ".join(parts)


def _observation_proxies_default() -> dict[str, float]:
    return {
        "cold_heat_lean": 0.5,
        "digestion_lean": 0.5,
        "activity_lean": 0.5,
        "moisture_lean": 0.5,
    }


def build_from_intake(intake_doc: dict[str, Any], *, sequence_id: str | None = None) -> dict[str, Any]:
    import importlib.util

    router_path = ROOT / "scripts" / "l0_red_flag_router_v1.py"
    spec = importlib.util.spec_from_file_location("l0_red_flag_router_v1", router_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("l0_red_flag_router_v1 missing")
    router = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router)

    enc = intake_doc.get("encounter") if isinstance(intake_doc.get("encounter"), dict) else {}
    ref_token = str(enc.get("ref_token") or "ENC-INTAKE-UNKNOWN")
    seq_id = sequence_id or f"SEQ-{re.sub(r'[^A-Za-z0-9]+', '-', ref_token)[:40]}-{_utc()[:10]}"
    intake = intake_doc.get("intake") if isinstance(intake_doc.get("intake"), dict) else {}
    sasang = intake.get("sasang_estimate") if isinstance(intake.get("sasang_estimate"), dict) else {}
    constitution = _constitution_from_label(str(sasang.get("label") or ""))
    confidence = 0.45 if constitution == "uncertain" else 0.55
    text_blob = _intake_text_blob(intake_doc)
    tpl = router.load_template()
    keyword_hits = router.keyword_hits_from_text(text_blob, tpl)
    l0_triggered = bool(keyword_hits)

    turns: list[dict[str, Any]] = []
    custom_turns = intake_doc.get("consultation_turns")
    if isinstance(custom_turns, list) and custom_turns:
        for i, t in enumerate(custom_turns):
            if not isinstance(t, dict):
                continue
            turns.append(
                {
                    "turn_index": int(t.get("turn_index", i)),
                    "ts_utc": str(t.get("ts_utc") or _utc()),
                    "turn_kind": str(t.get("turn_kind") or "follow_up_question"),
                    "observation_proxies": t.get("observation_proxies") or _observation_proxies_default(),
                    "ai_hypothesis": t.get("ai_hypothesis")
                    or {
                        "constitution": constitution,
                        "confidence": confidence,
                        "model_id": "intake_fusion_stub_v1",
                    },
                    "subjective_digest": str(t.get("subjective_digest") or text_blob[:500]),
                }
            )
    else:
        turn: dict[str, Any] = {
            "turn_index": 0,
            "ts_utc": _utc(),
            "turn_kind": "initial_survey",
            "modalities_present": {"survey": True, "birth_profile": True},
            "observation_proxies": _observation_proxies_default(),
            "ai_hypothesis": {
                "constitution": constitution,
                "confidence": confidence,
                "model_id": "intake_fusion_stub_v1",
                "rationale_short": "[HYPO] intake fusion 단일턴; 사상 가설만.",
            },
            "subjective_digest": text_blob[:2000],
        }
        if l0_triggered:
            turn["l0_red_flag"] = {
                "ts_utc": _utc(),
                "router_stage": "pre_turn",
                "turn_index": 0,
                "triggered": True,
                "keyword_hits": keyword_hits,
                "escalation_copy_id": "l0_red_flag_escalation_ko_v1",
                "non_gating": True,
            }
        turns.append(turn)

    traj = [str((t.get("ai_hypothesis") or {}).get("constitution") or "uncertain") for t in turns]
    confs = [float((t.get("ai_hypothesis") or {}).get("confidence") or 0.0) for t in turns]
    l0_events: list[dict[str, Any]] = []
    if l0_triggered:
        l0_events.append(
            {
                "ts_utc": _utc(),
                "router_stage": "pre_turn",
                "turn_index": 0,
                "triggered": True,
                "keyword_hits": keyword_hits,
                "escalation_copy_id": "l0_red_flag_escalation_ko_v1",
                "non_gating": True,
            }
        )

    return {
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
        "l0_router_events": l0_events,
        "turns": turns,
        "sequence_summary": {
            "turn_count": len(turns),
            "constitution_trajectory": traj,
            "confidence_trajectory": confs,
            "final_ai_constitution": traj[-1] if traj else "uncertain",
            "final_ai_confidence": confs[-1] if confs else 0.0,
        },
        "provenance": {"generator_id": "build_encounter_sequence_from_intake_v1.py"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sequence-id", default=None)
    ap.add_argument("--append-ledger", action="store_true")
    args = ap.parse_args()
    intake_doc = json.loads(args.intake_json.read_text(encoding="utf-8-sig"))
    doc = build_from_intake(intake_doc, sequence_id=args.sequence_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.append_ledger:
        import importlib.util

        ledger_path = ROOT / "scripts" / "encounter_sequence_ledger_v1.py"
        spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
        if spec is None or spec.loader is None:
            raise SystemExit(1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.append_encounter_sequence_line(ROOT, doc)
    print(json.dumps({"ok": True, "sequence_id": doc["encounter"]["sequence_id"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
