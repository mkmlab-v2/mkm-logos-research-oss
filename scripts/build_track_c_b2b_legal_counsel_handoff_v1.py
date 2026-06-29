#!/usr/bin/env python3
"""Rebuild Track C B2B legal counsel handoff from manifest + signoffs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
MANIFEST = ART / "track_c_b2b_counsel_export_manifest_v1_latest.json"
COUNSEL_SIGNOFF = ART / "track_c_b2b_legal_counsel_signoff_v1_latest.json"
COMMANDER_SIGNOFF = ART / "track_c_b2b_commander_signoff_v1_latest.json"
ZIP_META = ART / "track_c_b2b_counsel_zip_pack_v1_latest.json"
SCAN = ROOT / "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"
DEFAULT_OUT = ART / "track_c_b2b_legal_counsel_handoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    manifest = _read(MANIFEST) or {}
    counsel = _read(COUNSEL_SIGNOFF)
    commander = _read(COMMANDER_SIGNOFF)
    scan = _read(SCAN) or {}
    files = manifest.get("files") or []
    if counsel and counsel.get("status") == "COUNSEL_REVIEWED":
        posture = "COUNSEL_REVIEWED"
    elif commander:
        posture = "COMMANDER_PREFLIGHT_OK_PENDING_COUNSEL"
    elif scan.get("scan_ok"):
        posture = "PRECOUNSEL_SCAN_OK_PENDING_COUNSEL"
    else:
        posture = "PRECOUNSEL_SCAN_INCOMPLETE"
    external = bool(counsel and counsel.get("ready_for_external_send"))
    return {
        "schema": "track_c_b2b_legal_counsel_handoff_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "track_c_b2b",
        "ready_for_external_send": external,
        "legal_posture_status": posture,
        "counsel_signoff_required": not bool(counsel),
        "commander_signoff_recorded": bool(commander),
        "copy_scan_ok": scan.get("scan_ok"),
        "documents_for_counsel": [row.get("path") for row in files if isinstance(row, dict)],
        "file_manifest": files,
        "counsel_questions_ko": [
            "Two-Layer(Execution Lock + Meaning Lock) B2B 슬라이드의 투자·거래·면책 문구 적합성.",
            "OEM 파트너십 [HYPO] 표현이 계약상 과도한 확약으로 읽히지 않는지.",
            "Logos/성경 레이어 [NON_GATING] — 실전 트리거 오해 소지.",
            "레드액션 데모·와이어 수치의 IP·과장 공시 리스크.",
            "ready_for_external_send 승격 전 필수 체크리스트.",
        ],
        "explicit_non_claims": [
            "track_a_47_5_percent_headline",
            "lossless_compression",
            "omniscient_ai",
            "auto_live_trading_promotion",
            "wire_envelope_as_compression_kpi",
            "competitor_product_defamation",
        ],
        "counsel_pack_scripts": {
            "submission_chain": "scripts/Run-TrackCB2bCounselSubmissionPack_v1.ps1",
            "counsel_signoff_recorder": "scripts/record_track_c_b2b_legal_counsel_signoff_v1.py",
            "commander_signoff_recorder": "scripts/record_track_c_b2b_commander_signoff_v1.py",
            "zip_meta": ZIP_META.relative_to(ROOT).as_posix(),
            "email_draft": "docs/final/artifacts/track_c_b2b_counsel_submission_email_draft_v1_latest.json",
            "one_minute_brief": "reports/track_c_b2b_counsel_one_minute_brief_v1_latest.md",
        },
        "business_ssot": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.8.1",
        "boundary_ack": "Handoff manifest only; not legal approval unless counsel signoff on disk.",
        "counsel_signoff": counsel,
        "commander_signoff": commander,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "legal_posture_status": doc["legal_posture_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
