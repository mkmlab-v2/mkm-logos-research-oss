#!/usr/bin/env python3
"""TKM encounter_sequence L5 myeongni_ref sidecar helpers [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REF_TOKEN_MYEONGNI_MAP: dict[str, str] = {
    "ENC-PARK-GEUMJA-2026": "reports/park_geumja_myeongni_full_latest.json",
    "PARK-GEUMJA-SENIOR-2026-001": "reports/park_geumja_myeongni_full_latest.json",
}

DEFAULT_MYEONGNI_REF = "reports/myeongni_physician_gold_stub_v1_latest.json"
STUB_FIXTURE = ROOT / "tests/fixtures/myeongni_physician_gold_stub_v1.example.json"


def _engine_report_relpath(ref_token: str) -> str:
    import importlib.util

    path = ROOT / "scripts/tkm_physician_gold_birth_profile_v1.py"
    spec = importlib.util.spec_from_file_location("tkm_physician_gold_birth_profile_v1", path)
    if spec is None or spec.loader is None:
        return ""
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return str(mod.engine_report_relpath(ref_token))


def _is_engine_report(ref_rel: str) -> bool:
    path = ROOT / ref_rel
    if not path.is_file():
        return False
    norm = ref_rel.replace("\\", "/")
    if "/myeongni_physician_gold_engine/" in norm:
        return True
    if "myeongni_physician_gold_stub" in norm:
        return False
    try:
        body = json.loads(path.read_text(encoding="utf-8-sig"))
        meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
        if meta.get("stub") is True:
            return False
        if meta.get("engine_built") is True:
            return True
        if body.get("schema") == "myeongni_full_report_v1" and isinstance(body.get("birth_engine"), dict):
            return True
    except Exception:
        return False
    return False


def latest_records_by_sequence_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seq: dict[str, dict[str, Any]] = {}
    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if seq_id:
            by_seq[seq_id] = row
    return list(by_seq.values())


def birth_profile_present(record: dict[str, Any]) -> bool:
    for turn in record.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        mods = turn.get("modalities_present")
        if isinstance(mods, dict) and mods.get("birth_profile") is True:
            return True
    return False


def _ref_token(record: dict[str, Any]) -> str:
    enc = record.get("encounter") if isinstance(record.get("encounter"), dict) else {}
    return str(enc.get("ref_token") or "")


def resolve_myeongni_report_ref(record: dict[str, Any], *, capture: dict[str, Any] | None = None) -> str | None:
    if capture:
        meta = capture.get("meta") if isinstance(capture.get("meta"), dict) else {}
        explicit = meta.get("myeongni_report_ref")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip().replace("\\", "/")
        intake_ref = str(capture.get("intake_ref") or "")
        if "park_geumja" in intake_ref:
            return REF_TOKEN_MYEONGNI_MAP["ENC-PARK-GEUMJA-2026"]
    token = _ref_token(record)
    if token in REF_TOKEN_MYEONGNI_MAP:
        mapped = REF_TOKEN_MYEONGNI_MAP[token]
        if (ROOT / mapped).is_file():
            return mapped
    if token:
        engine_rel = _engine_report_relpath(token)
        if engine_rel and (ROOT / engine_rel).is_file():
            return engine_rel
    if token.startswith("ENC-PHYSICIAN-GOLD") or birth_profile_present(record):
        stub = ROOT / DEFAULT_MYEONGNI_REF
        if stub.is_file():
            return DEFAULT_MYEONGNI_REF
    return None


def _load_myeongni_report(ref_rel: str) -> dict[str, Any] | None:
    path = ROOT / ref_rel
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_cross_assessor():
    import importlib.util

    path = ROOT / "scripts/core/patient_intake_myeongni_sasang_cross_v1.py"
    spec = importlib.util.spec_from_file_location("patient_intake_myeongni_sasang_cross_v1", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compute_cross_check_status(record: dict[str, Any], report: dict[str, Any] | None) -> str:
    if not report:
        return "not_computed"
    summary = record.get("sequence_summary") if isinstance(record.get("sequence_summary"), dict) else {}
    label = str(summary.get("final_ai_constitution") or "uncertain")
    try:
        cross_mod = _load_cross_assessor()
        if cross_mod is None:
            return "not_computed"
        cross = cross_mod.assess_myeongni_sasang_cross(report, label)
        return str(cross.get("status") or "insufficient")
    except Exception:
        return "not_computed"


def build_sidecar(
    record: dict[str, Any],
    *,
    capture: dict[str, Any] | None = None,
    myeongni_report_ref: str | None = None,
) -> dict[str, Any] | None:
    if not birth_profile_present(record):
        return None
    ref = myeongni_report_ref or resolve_myeongni_report_ref(record, capture=capture)
    if not ref:
        return None
    report = _load_myeongni_report(ref)
    cross = compute_cross_check_status(record, report)
    return {
        "hypothesis_tier": "B",
        "non_gating": True,
        "birth_profile_present": True,
        "myeongni_report_ref": ref.replace("\\", "/"),
        "cross_check_status": cross,
        "sasang_lens_separation_ok": True,
        "note_ko": "[HYPO] L5 명리 보조층; 사상 ai_hypothesis와 자동 합선 금지.",
    }


def attach_sidecar(
    record: dict[str, Any],
    *,
    capture: dict[str, Any] | None = None,
    myeongni_report_ref: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    out = dict(record)
    if out.get("l5_myeongni_ref") and not force:
        return out
    sidecar = build_sidecar(out, capture=capture, myeongni_report_ref=myeongni_report_ref)
    if sidecar:
        out["l5_myeongni_ref"] = sidecar
    return out


def validate_sasang_lens_separation(record: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    sidecar = record.get("l5_myeongni_ref")
    if not isinstance(sidecar, dict):
        return errs
    if sidecar.get("sasang_lens_separation_ok") is not True:
        errs.append("l5_myeongni_ref.sasang_lens_separation_ok must be true")
    forbidden = ("constitution", "final_ai_constitution", "sasang_label")
    for key in forbidden:
        if key in sidecar:
            errs.append(f"l5_myeongni_ref must not contain {key}")
    if sidecar.get("non_gating") is not True:
        errs.append("l5_myeongni_ref.non_gating must be true")
    return errs


def ensure_stub_report() -> Path:
    out = ROOT / "reports/myeongni_physician_gold_stub_v1_latest.json"
    if out.is_file():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    if STUB_FIXTURE.is_file():
        out.write_text(STUB_FIXTURE.read_text(encoding="utf-8-sig"), encoding="utf-8")
    return out
