#!/usr/bin/env python3
"""C12 commander pack — OpenData 327 human gate checklist + artifact paths (Fact-Lock)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "reports/opendata_327_submission_readiness_latest.json"
HANDOFF = ROOT / "reports/opendata_327_commander_handoff_latest.json"
FORBIDDEN = ROOT / "reports/opendata_327_forbidden_grep_latest.json"
MERGE = ROOT / "reports/opendata_327_pdf_merge_latest.json"
DEFAULT_OUT = ROOT / "reports/opendata_327_c12_commander_pack_v1_latest.json"
FINAL_PDF = ROOT / "reports/moksori_ai_opendata327_task1_business_plan_v1.pdf"
DRAFT_COVER = ROOT / "reports/opendata_327_part_a_cover_draft_v1.pdf"
PART_B_MD = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def build() -> dict[str, Any]:
    readiness = _load(READINESS)
    handoff = _load(HANDOFF)
    forbidden = _load(FORBIDDEN)
    merge = _load(MERGE)

    final_exists = FINAL_PDF.is_file()
    final_kb = round(FINAL_PDF.stat().st_size / 1024, 1) if final_exists else None

    tasks = [
        {
            "id": "C12-A",
            "title": "표지 A — K-Startup 공식 양식",
            "owner": "human",
            "status": "draft_merged_preview_ok",
            "now": _rel(DRAFT_COVER) + " 병합된 미리보기는 " + _rel(FINAL_PDF),
            "action": (
                "공고 별첨 표지 PDF를 받아 저장 후: "
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/Run-OpenData327FinalUploadBundle_v1.ps1 "
                "-OfficialCoverPdf <공식표지.pdf> -SubmitDateKst 2026-06-05"
            ),
            "done_when": "final_upload_pdf가 공식 표지로 재병합됨",
        },
        {
            "id": "C12-22",
            "title": "§2-2 성능 목표 수치",
            "owner": "human",
            "status": "md_ok_pending_eyeball",
            "evidence": _rel(PART_B_MD) + " §2-2 (95%/90%/20%/2영업일/25초)",
            "action": "내부 벤치 1회 대조 후 표 수치 확정(과제 KPI 유지·Track A 수치 금지)",
            "done_when": "육안 검수 체크",
        },
        {
            "id": "C12-G3",
            "title": "특허·출원번호 (G3)",
            "owner": "human",
            "status": "not_in_body",
            "action": "실제 접수 후에만 출원번호·일자 기재. 미접수 시 변리사 일정 문구만 유지",
            "done_when": "제출본에 허위 출원번호 없음",
        },
        {
            "id": "C12-G5",
            "title": "공고 파란 안내 문구 (G5)",
            "owner": "human",
            "status": "export_clean",
            "action": "최종 PDF에서 파란/안내 문구 없는지 육안. MD는 이미 strip",
            "done_when": "제출 PDF 검정 완료",
        },
        {
            "id": "C12-UP",
            "title": "K-Startup 업로드",
            "owner": "human",
            "status": "blocked_until_C12-A",
            "deadline_kst": readiness.get("deadline_kst"),
            "action": "technical_ready 후 포털 dry-run → 6/5 18:00 전 최종 제출",
            "done_when": "ready_for_kstartup_upload=true (readiness JSON)",
        },
    ]

    return {
        "schema": "opendata_327_c12_commander_pack_v1",
        "generated_at_utc": _utc_now(),
        "deadline_kst": readiness.get("deadline_kst", "2026-06-05T18:00:00+09:00"),
        "legal_entity": readiness.get("legal_entity", "주식회사 목소리네트워크"),
        "technical_ready_for_pdf_bundle": readiness.get("technical_ready_for_pdf_bundle"),
        "ready_for_kstartup_upload": readiness.get("ready_for_kstartup_upload"),
        "cover_a_merged": readiness.get("cover_a_merged"),
        "cover_is_draft": True,
        "g4_forbidden_grep": {
            "ok": forbidden.get("ok"),
            "hits": forbidden.get("hits", forbidden.get("hit_count")),
        },
        "section_2_2": readiness.get("section_2_2"),
        "artifacts": {
            "final_upload_pdf": {
                "path": _rel(FINAL_PDF),
                "exists": final_exists,
                "size_kb": final_kb,
            },
            "draft_cover_pdf": _rel(DRAFT_COVER),
            "bcd_merged_no_cover": merge.get("output_pdf"),
            "submission_md": _rel(PART_B_MD),
            "readiness": _rel(READINESS),
            "handoff": _rel(HANDOFF),
        },
        "automated_completed_this_session": [
            "Run-OpenData327SubmissionPrep_v1.ps1 exit 0",
            "G4 forbidden grep hits=0",
            "DRAFT cover export + merge -> moksori_ai_opendata327_task1_business_plan_v1.pdf",
        ],
        "c12_tasks": tasks,
        "one_liners": {
            "prep": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-OpenData327SubmissionPrep_v1.ps1",
            "official_merge": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/Run-OpenData327FinalUploadBundle_v1.ps1 "
                "-OfficialCoverPdf <path> -SubmitDateKst 2026-06-05"
            ),
            "open_pdf": f"start {FINAL_PDF}",
        },
        "track_wall": "separate_from_LG_compression_OEM",
        "boundary_ack": "C12 human gates remain; DRAFT cover is not upload-ready.",
        "pointers": handoff.get("pointers") or readiness.get("pointers"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "tasks": len(doc["c12_tasks"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
