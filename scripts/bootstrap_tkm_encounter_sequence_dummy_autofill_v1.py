#!/usr/bin/env python3
"""Bootstrap TKM encounter_sequence + clinic MVP with idempotent dummy rows [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_dummy_autofill_v1_latest.json"

ENC_FIXTURE = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
DISAGREE_FIXTURE = ROOT / "tests/fixtures/encounter_sequence_disagreement_v1.example.json"
CLINIC_DISAGREE_FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_disagreement_v1.example.json"

DUMMY_CLINIC_SPECS: list[dict[str, Any]] = [
    {
        "ref_token": "ENC-DUMMY-AUTO-01",
        "sequence_id": "SEQ-DUMMY-AUTO-01",
        "ai": "taeyang",
        "physician": "soeum",
        "confidence": 0.79,
        "match": False,
        "code": "ai_overconfident",
    },
    {
        "ref_token": "ENC-DUMMY-AUTO-02",
        "sequence_id": "SEQ-DUMMY-AUTO-02",
        "ai": "soyang",
        "physician": "soyang",
        "confidence": 0.56,
        "match": True,
        "code": "none",
    },
    {
        "ref_token": "ENC-DUMMY-AUTO-03",
        "sequence_id": "SEQ-DUMMY-AUTO-03",
        "ai": "taeeum",
        "physician": "taeeum",
        "confidence": 0.48,
        "match": True,
        "code": "none",
    },
    {
        "ref_token": "ENC-DUMMY-AUTO-04",
        "sequence_id": "SEQ-DUMMY-AUTO-04",
        "ai": "soeum",
        "physician": "taeyang",
        "confidence": 0.42,
        "match": False,
        "code": "ai_underconfident",
    },
    {
        "ref_token": "ENC-DUMMY-AUTO-05",
        "sequence_id": "SEQ-DUMMY-AUTO-05",
        "ai": "uncertain",
        "physician": "withheld",
        "confidence": 0.35,
        "match": False,
        "code": "physician_withheld",
    },
]


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


def _clinic_rows() -> list[dict[str, Any]]:
    base = ROOT / "data/clinic"
    rows: list[dict[str, Any]] = []
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _encounter_sequence_ids() -> set[str]:
    mod = _load_mod("encounter_sequence_ledger_v1", "scripts/encounter_sequence_ledger_v1.py")
    return {
        str((r.get("encounter") or {}).get("sequence_id") or "")
        for r in mod.iter_ledger_records(ROOT)
    }


def _build_dummy_clinic_capture(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "version": "1.0.0",
        "ts_utc": _utc(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "encounter": {"ref_token": spec["ref_token"]},
        "modalities_present": {
            "survey": True,
            "face_image": False,
            "voice_sample": False,
            "birth_profile": True,
        },
        "observation_proxies": {
            "cold_heat_lean": 0.5,
            "digestion_lean": 0.5,
            "activity_lean": 0.5,
            "moisture_lean": 0.5,
        },
        "ai_hypothesis": {
            "constitution": spec["ai"],
            "confidence": spec["confidence"],
            "model_id": "dummy_autofill_v1",
            "rationale_short": "[HYPO][DUMMY] 자동 채움; 임상 단정·Track A 승격 금지.",
        },
        "physician_constitution": {
            "label": spec["physician"],
            "recorded_by_role": "licensed_km_physician",
            "notes": "[DUMMY] bootstrap autofill only",
        },
        "agreement": {
            "ai_physician_match": spec["match"],
            "disagreement_code": spec["code"],
        },
        "intake_ref": "reports/patient_intake_fusion_bundle_draft_latest.json",
        "patient_facing_copy_ack": True,
        "meta": {"dummy_autofill": True, "research_only": True},
    }


def autofill(*, min_clinic_captures: int = 5) -> dict[str, Any]:
    ingest_mod = _load_mod(
        "ingest_clinic_capture_to_encounter_sequence_v1",
        "scripts/ingest_clinic_capture_to_encounter_sequence_v1.py",
    )
    ledger_mod = _load_mod("encounter_sequence_ledger_v1", "scripts/encounter_sequence_ledger_v1.py")
    apply_mod = _load_mod(
        "apply_encounter_sequence_curated_learning_v1",
        "scripts/apply_encounter_sequence_curated_learning_v1.py",
    )
    draft_mod = _load_mod(
        "build_encounter_sequence_curated_learning_draft_v1",
        "scripts/build_encounter_sequence_curated_learning_draft_v1.py",
    )

    steps: list[dict[str, Any]] = []
    seq_ids = _encounter_sequence_ids()

    for fixture, seq_key in (
        (ENC_FIXTURE, "SEQ-2026-0618-01"),
        (DISAGREE_FIXTURE, "SEQ-DISAGREE-01"),
    ):
        if seq_key not in seq_ids and fixture.is_file():
            doc = json.loads(fixture.read_text(encoding="utf-8-sig"))
            ledger_mod.append_encounter_sequence_line(ROOT, doc)
            steps.append({"kind": "encounter_fixture", "sequence_id": seq_key, "applied": True})
            seq_ids.add(seq_key)

    if CLINIC_DISAGREE_FIXTURE.is_file():
        cap = json.loads(CLINIC_DISAGREE_FIXTURE.read_text(encoding="utf-8-sig"))
        res = ingest_mod.ingest(cap, append_clinic_ledger=True, sequence_id="SEQ-CLINIC-P19-01")
        steps.append({"kind": "clinic_fixture_p19", **res})

    existing_refs = {
        str((r.get("encounter") or {}).get("ref_token") or "") for r in _clinic_rows()
    }
    for spec in DUMMY_CLINIC_SPECS:
        ref = spec["ref_token"]
        if ref in existing_refs:
            steps.append({"kind": "clinic_dummy", "ref_token": ref, "already_present": True})
            continue
        cap = _build_dummy_clinic_capture(spec)
        res = ingest_mod.ingest(
            cap,
            append_clinic_ledger=True,
            sequence_id=str(spec["sequence_id"]),
        )
        existing_refs.add(ref)
        steps.append({"kind": "clinic_dummy", "ref_token": ref, **res})

    clinic_count = len(_clinic_rows())
    if clinic_count < min_clinic_captures:
        extra_i = 0
        while clinic_count < min_clinic_captures:
            extra_i += 1
            ref = f"ENC-DUMMY-AUTO-X{extra_i:02d}"
            if ref in existing_refs:
                clinic_count = len(_clinic_rows())
                continue
            spec = {
                "ref_token": ref,
                "sequence_id": f"SEQ-DUMMY-AUTO-X{extra_i:02d}",
                "ai": "taeeum",
                "physician": "soeum",
                "confidence": 0.5,
                "match": False,
                "code": "modality_insufficient",
            }
            cap = _build_dummy_clinic_capture(spec)
            ingest_mod.ingest(cap, append_clinic_ledger=True, sequence_id=spec["sequence_id"])
            existing_refs.add(ref)
            clinic_count = len(_clinic_rows())
            steps.append({"kind": "clinic_dummy_extra", "ref_token": ref, "applied": True})

    draft_doc = draft_mod.build()
    apply_doc = apply_mod.apply(human_gate_ack=False, dummy_auto_fill=True)
    steps.append({"kind": "curated_draft", "draft_count": draft_doc.get("disagreement_draft_count")})
    steps.append({"kind": "curated_apply", **apply_doc})

    return {
        "schema": "tkm_encounter_sequence_dummy_autofill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "dummy_autofill": True,
        "research_only": True,
        "clinic_capture_count": len(_clinic_rows()),
        "encounter_sequence_count": len(_encounter_sequence_ids()),
        "min_clinic_captures_target": min_clinic_captures,
        "autofill_ok": apply_doc.get("applied") is True or apply_doc.get("dummy_autofill") is True,
        "steps": steps,
        "reproduce": "py scripts/bootstrap_tkm_encounter_sequence_dummy_autofill_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-clinic-captures", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = autofill(min_clinic_captures=args.min_clinic_captures)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["autofill_ok"],
                "clinic_capture_count": doc["clinic_capture_count"],
                "encounter_sequence_count": doc["encounter_sequence_count"],
            }
        )
    )
    return 0 if doc["autofill_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
