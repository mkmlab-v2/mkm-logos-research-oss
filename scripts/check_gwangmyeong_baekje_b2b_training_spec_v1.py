#!/usr/bin/env python3
"""[HYPO] Static barrier audit for gwangmyeong B2B training spec (no live Solapi/Form API)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json"
DEFAULT_OUT = ROOT / "reports/gwangmyeong_baekje_b2b_barrier_audit_v1_latest.json"

INTAKE_WEBHOOK_MARKERS = (
    "KAKAO_CLINIC_INTAKE_WEBHOOK",
    "kakao_clinic_intake",
    "patient_intake",
    "환자 유치",
    "환자 소개",
    "소개 보상",
    "성과 보상",
    "내원 안내",
    "진료 예약",
)

TEMPLATE_FORBIDDEN = (
    "보수교육",
    "AKOM",
    "임상 자격",
    "환자 소개",
    "소개비",
    "kickback",
    "완치",
    "효능을 보장합니다",
    "효능을 보장함",
)

CERT_FORBIDDEN = (
    "보수교육",
    "임상 자격 보증",
    "AKOM 인정",
    "치료 효능",
    "환자 소개 권한",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_strings(obj: Any) -> str:
    if isinstance(obj, dict):
        return "\n".join(_collect_strings(v) for v in obj.values())
    if isinstance(obj, list):
        return "\n".join(_collect_strings(v) for v in obj)
    return str(obj)


def _talk_corpus(spec: dict[str, Any]) -> str:
    talk = spec.get("automated_talk_loop_4weeks") or {}
    return _collect_strings(talk.get("templates") or {})


def _barrier_01(spec: dict[str, Any]) -> dict[str, Any]:
    talk = _talk_corpus(spec)
    forms = _collect_strings(spec.get("google_form_json_schemas") or {})
    corpus = talk + "\n" + forms
    hits = [m for m in INTAKE_WEBHOOK_MARKERS if m.lower() in corpus.lower()]
    ok = not any(
        x in corpus
        for x in ("KAKAO_CLINIC_INTAKE_WEBHOOK_URL", "kakao_clinic_intake_webhook")
    )
    return {
        "id": "BARRIER-01",
        "ok": ok and not hits,
        "status": "PASS" if ok and not hits else "FAIL",
        "evidence": {
            "no_intake_webhook_in_operational_text": ok,
            "forbidden_marker_hits": hits,
        },
        "note": "Static only; live webhook routing must stay separate at deploy.",
    }


def _barrier_02(spec: dict[str, Any]) -> dict[str, Any]:
    corpus = _talk_corpus(spec)
    hits = [w for w in TEMPLATE_FORBIDDEN if w in corpus]
    send_hold = spec.get("governance", {}).get("send_gate") == "HOLD"
    ready = spec.get("governance", {}).get("ready_for_external_send") is False
    ok = not hits and send_hold and ready
    return {
        "id": "BARRIER-02",
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "evidence": {
            "forbidden_substring_hits_in_talk_templates": hits,
            "send_gate_HOLD": send_hold,
            "ready_for_external_send_false": ready,
        },
    }


def _barrier_03(spec: dict[str, Any]) -> dict[str, Any]:
    forms = spec.get("google_form_json_schemas") or {}
    qa = forms.get("FORM-03_qa_barrier") or {}
    fields = qa.get("fields") or {}
    pledge = fields.get("de_identification_pledge", {})
    cert = spec.get("certificate_wording") or {}
    forbidden = cert.get("forbidden") or []
    corpus = _talk_corpus(spec)
    cert_hits = [w for w in forbidden if w in corpus and w != "치료 효능"]
    ok = pledge.get("required") is True and not cert_hits
    return {
        "id": "BARRIER-03",
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "evidence": {
            "qa_de_identification_pledge_required": pledge.get("required") is True,
            "certificate_forbidden_in_talk_templates": cert_hits,
            "certificate_forbidden_list": forbidden,
        },
    }


def _asset_pointers(spec: dict[str, Any], root: Path) -> dict[str, Any]:
    assets = spec.get("education_assets_b2b_only") or {}
    checks = []
    for key in (
        "rib55_pilot_pointer",
        "staff_handout_pointer",
        "staff_integrated_pointer",
    ):
        rel = assets.get(key)
        if not rel:
            checks.append({"key": key, "ok": False, "reason": "missing pointer"})
            continue
        path = root / str(rel).replace("/", "\\") if "\\" not in str(rel) else root / rel
        path = root / str(rel).replace("\\", "/")
        checks.append({"key": key, "path": str(rel), "ok": path.is_file()})
    return {"checks": checks, "ok": all(c["ok"] for c in checks)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-spec-status", action="store_true")
    args = ap.parse_args()

    if not args.spec.is_file():
        raise SystemExit(f"missing spec: {args.spec}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    barriers = [
        _barrier_01(spec),
        _barrier_02(spec),
        _barrier_03(spec),
    ]
    assets = _asset_pointers(spec, ROOT)
    all_ok = all(b["ok"] for b in barriers) and assets["ok"]

    doc = {
        "schema": "gwangmyeong_baekje_b2b_barrier_audit_v1",
        "generated_at_utc": _utc(),
        "spec": str(args.spec.relative_to(ROOT)).replace("\\", "/"),
        "research_only": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "barriers": barriers,
        "education_assets": assets,
        "audit_status": "PASS" if all_ok else "FAIL",
        "ok": all_ok,
        "reproduce": "py scripts/check_gwangmyeong_baekje_b2b_training_spec_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_spec_status:
        checklist = spec.setdefault("patient_funnel_isolation_checklist", {})
        checklist["audit_status"] = doc["audit_status"]
        checklist["last_audit_at_utc"] = doc["generated_at_utc"]
        checklist["last_audit_report"] = str(args.out.relative_to(ROOT)).replace("\\", "/")
        for rule in checklist.get("rules") or []:
            rid = rule.get("id")
            match = next((b for b in barriers if b["id"] == rid), None)
            if match:
                rule["status"] = match["status"]
        spec.setdefault("reproduction", {})["validate_cmd"] = doc["reproduce"]
        args.spec.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": all_ok, "out": str(args.out), "audit_status": doc["audit_status"]}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
