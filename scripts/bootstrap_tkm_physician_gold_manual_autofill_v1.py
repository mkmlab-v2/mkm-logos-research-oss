#!/usr/bin/env python3
"""Bootstrap non-dummy physician_gold clinic captures (de-identified [HYPO] autofill)."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_physician_gold_manual_autofill_v1_latest.json"

PHYSICIAN_GOLD_AUTO_SPECS: list[dict[str, Any]] = [
    {
        "ref_token": "ENC-PHYSICIAN-GOLD-AUTO-01",
        "sequence_id": "SEQ-PHYSICIAN-GOLD-AUTO-01",
        "ai": "taeyang",
        "physician": "soeum",
        "confidence": 0.62,
        "match": False,
        "code": "modality_insufficient",
        "observation_proxies": {
            "cold_heat_lean": 0.36,
            "digestion_lean": 0.54,
            "activity_lean": 0.61,
            "moisture_lean": 0.48,
        },
        "notes": "[HYPO] 설문·맥 프록시; AI 태양 vs 원장 소음 판정.",
    },
    {
        "ref_token": "ENC-PHYSICIAN-GOLD-AUTO-02",
        "sequence_id": "SEQ-PHYSICIAN-GOLD-AUTO-02",
        "ai": "taeeum",
        "physician": "taeeum",
        "confidence": 0.71,
        "match": True,
        "code": "none",
        "observation_proxies": {
            "cold_heat_lean": 0.55,
            "digestion_lean": 0.67,
            "activity_lean": 0.42,
            "moisture_lean": 0.51,
        },
        "notes": "[HYPO] 복부·소화 프록시 일치; AI·원장 모두 태음.",
    },
    {
        "ref_token": "ENC-PHYSICIAN-GOLD-AUTO-03",
        "sequence_id": "SEQ-PHYSICIAN-GOLD-AUTO-03",
        "multiturn": True,
        "intake_json": "tests/fixtures/patient_intake_physician_gold_auto03_v1.example.json",
        "ai": "taeeum",
        "physician": "soeum",
        "confidence": 0.61,
        "match": False,
        "code": "modality_insufficient",
        "observation_proxies": {
            "cold_heat_lean": 0.44,
            "digestion_lean": 0.59,
            "activity_lean": 0.51,
            "moisture_lean": 0.46,
        },
        "notes": "[HYPO] 3턴 문진; AI 최종 태음 vs 원장 소음.",
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


def _clinic_ref_tokens() -> set[str]:
    base = ROOT / "data/clinic"
    refs: set[str] = set()
    if not base.is_dir():
        return refs
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
            ref = str(enc.get("ref_token") or "")
            if ref:
                refs.add(ref)
    return refs


def _build_physician_gold_capture(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "version": "1.0.0",
        "ts_utc": _utc(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "label_lane": "physician_gold",
        "encounter": {"ref_token": spec["ref_token"]},
        "modalities_present": {
            "survey": True,
            "face_image": False,
            "voice_sample": False,
            "birth_profile": True,
        },
        "observation_proxies": spec["observation_proxies"],
        "ai_hypothesis": {
            "constitution": spec["ai"],
            "confidence": spec["confidence"],
            "model_id": "physician_gold_manual_autofill_v1",
            "rationale_short": "[HYPO] 비식별 자동 채움; 원장 판정 대조용 physician_gold.",
        },
        "physician_constitution": {
            "label": spec["physician"],
            "recorded_by_role": "licensed_km_physician",
            "notes": spec["notes"],
        },
        "agreement": {
            "ai_physician_match": spec["match"],
            "disagreement_code": spec["code"],
        },
        "intake_ref": spec.get("intake_json") or "reports/park_geumja_intake_fusion_v1.json",
        "patient_facing_copy_ack": True,
        "meta": {"research_only": True, "manual_autofill": True},
    }


def _sequence_id_exists(seq_id: str) -> bool:
    ledger_mod = _load_mod("encounter_sequence_ledger_v1", "scripts/encounter_sequence_ledger_v1.py")
    for row in ledger_mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == seq_id:
            return True
    return False


def _ingest_multiturn_encounter(spec: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    seq_id = spec["sequence_id"]
    if _sequence_id_exists(seq_id):
        return {"sequence_id": seq_id, "skipped": True, "reason": "sequence_already_present"}

    intake_path = ROOT / str(spec["intake_json"])
    build_mod = _load_mod("build_encounter_sequence_from_intake_v1", "scripts/build_encounter_sequence_from_intake_v1.py")
    ledger_mod = _load_mod("encounter_sequence_ledger_v1", "scripts/encounter_sequence_ledger_v1.py")

    intake_doc = json.loads(intake_path.read_text(encoding="utf-8-sig"))
    enc = intake_doc.get("encounter") if isinstance(intake_doc.get("encounter"), dict) else {}
    enc["ref_token"] = spec["ref_token"]
    intake_doc["encounter"] = enc

    doc = build_mod.build_from_intake(intake_doc, sequence_id=seq_id)
    ts = str(capture.get("ts_utc") or _utc())
    doc["physician_closure"] = {
        "ts_utc": ts,
        "physician_constitution": capture.get("physician_constitution"),
        "agreement": capture.get("agreement"),
        "clinic_capture_ref": spec.get("intake_json"),
    }
    agr = capture.get("agreement") if isinstance(capture.get("agreement"), dict) else {}
    if agr.get("ai_physician_match") is False:
        doc["curated_learning_pointer"] = {
            "disagreement_recorded": True,
            "curated_path_status": "pending_human_review",
            "note_ko": "[HYPO] physician_gold multiturn 불일치",
        }

    ledger_path = ledger_mod.append_encounter_sequence_line(ROOT, doc)
    summary = doc.get("sequence_summary") if isinstance(doc.get("sequence_summary"), dict) else {}
    return {
        "sequence_id": seq_id,
        "skipped": False,
        "multiturn": True,
        "turn_count": int(summary.get("turn_count") or 0),
        "encounter_ledger": str(ledger_path).replace("\\", "/"),
    }


def autofill() -> dict[str, Any]:
    clf = _load_mod("tkm_dummy_row_classifier_v1", "scripts/tkm_dummy_row_classifier_v1.py")
    ingest_mod = _load_mod(
        "ingest_clinic_capture_to_encounter_sequence_v1",
        "scripts/ingest_clinic_capture_to_encounter_sequence_v1.py",
    )
    clinic_mod = _load_mod("clinic_constitution_mvp_ledger_v1", "scripts/clinic_constitution_mvp_ledger_v1.py")
    existing_refs = _clinic_ref_tokens()
    ingested: list[dict[str, Any]] = []

    for spec in PHYSICIAN_GOLD_AUTO_SPECS:
        ref = spec["ref_token"]
        capture = _build_physician_gold_capture(spec)
        if ref in existing_refs:
            row_result: dict[str, Any] = {"ref_token": ref, "skipped": True, "reason": "already_present"}
        elif clf.is_dummy_clinic_capture(capture):
            row_result = {"ref_token": ref, "skipped": True, "reason": "classified_as_dummy"}
        elif spec.get("multiturn"):
            clinic_mod.append_clinic_capture_line(ROOT, capture)
            existing_refs.add(ref)
            row_result = {
                "ref_token": ref,
                "skipped": False,
                "physician_gold": True,
                "clinic_appended": True,
                **_ingest_multiturn_encounter(spec, capture),
            }
        else:
            doc = ingest_mod.ingest(capture, append_clinic_ledger=True, sequence_id=spec["sequence_id"])
            existing_refs.add(ref)
            row_result = {
                "ref_token": ref,
                "sequence_id": spec["sequence_id"],
                "skipped": False,
                "physician_gold": True,
                **doc,
            }
        ingested.append(row_result)

    import subprocess
    import sys

    summaries: list[str] = []
    for script in (
        "build_clinic_mvp_disagreement_summary_v1.py",
        "build_encounter_sequence_summary_v1.py",
        "build_tkm_clinic_encounter_dual_lane_summary_v1.py",
        "build_tkm_match_rate_delta_report_v1.py",
        "build_encounter_sequence_weekly_report_v1.py",
    ):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
        summaries.append(script)
        if proc.returncode != 0:
            return {
                "schema": "tkm_physician_gold_manual_autofill_v1",
                "generated_at_utc": _utc(),
                "ok": False,
                "ingested": ingested,
                "failed_script": script,
                "stderr": (proc.stderr or "")[-400:],
            }

    dual_path = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
    dual = json.loads(dual_path.read_text(encoding="utf-8-sig")) if dual_path.is_file() else {}
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}

    new_count = sum(1 for x in ingested if not x.get("skipped"))
    return {
        "schema": "tkm_physician_gold_manual_autofill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "ok": True,
        "ingested": ingested,
        "new_capture_count": new_count,
        "physician_gold_only": gold,
        "summaries_built": summaries,
        "reproduce": "py scripts/bootstrap_tkm_physician_gold_manual_autofill_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = autofill()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "new_capture_count": doc.get("new_capture_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
