#!/usr/bin/env python3
"""Multi-turn consultation_turns → encounter_sequence smoke [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/encounter_sequence_multiturn_smoke_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/patient_intake_multiturn_v1.example.json"
SEQ_ID = "SEQ-MULTITURN-P21-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_smoke(*, intake_path: Path = FIXTURE, sequence_id: str = SEQ_ID) -> dict:
    build_mod = _load_mod("build_encounter_sequence_from_intake_v1", "scripts/build_encounter_sequence_from_intake_v1.py")
    ledger_mod = _load_mod("encounter_sequence_ledger_v1", "scripts/encounter_sequence_ledger_v1.py")

    intake_doc = json.loads(intake_path.read_text(encoding="utf-8-sig"))
    doc = build_mod.build_from_intake(intake_doc, sequence_id=sequence_id)
    summary = doc.get("sequence_summary") if isinstance(doc.get("sequence_summary"), dict) else {}
    turn_count = int(summary.get("turn_count") or 0)
    traj = summary.get("constitution_trajectory") if isinstance(summary.get("constitution_trajectory"), list) else []
    confs = summary.get("confidence_trajectory") if isinstance(summary.get("confidence_trajectory"), list) else []

    doc["physician_closure"] = {
        "ts_utc": _utc(),
        "physician_constitution": {
            "label": "taeeum",
            "recorded_by_role": "licensed_km_physician",
            "notes": "[HYPO] multi-turn smoke closure",
        },
        "agreement": {
            "ai_physician_match": True,
            "disagreement_code": "none",
        },
    }

    existing = {
        str((r.get("encounter") or {}).get("sequence_id") or "")
        for r in ledger_mod.iter_ledger_records(ROOT)
    }
    if sequence_id not in existing:
        ledger_mod.append_encounter_sequence_line(ROOT, doc)

    smoke_ok = turn_count >= 3 and len(traj) >= 3 and len(confs) >= 3 and confs[-1] > confs[0]
    return {
        "schema": "encounter_sequence_multiturn_smoke_v1",
        "generated_at_utc": _utc(),
        "smoke_ok": smoke_ok,
        "sequence_id": sequence_id,
        "turn_count": turn_count,
        "constitution_trajectory": traj,
        "confidence_trajectory": confs,
        "confidence_delta_last_minus_first": round(confs[-1] - confs[0], 4) if confs else None,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake-json", type=Path, default=FIXTURE)
    ap.add_argument("--sequence-id", default=SEQ_ID)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run_smoke(intake_path=args.intake_json, sequence_id=args.sequence_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["smoke_ok"], "turn_count": doc["turn_count"]}))
    return 0 if doc["smoke_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
