#!/usr/bin/env python3
"""Fused OpenData 327 commander handoff — gates, PDFs, human calendar (one JSON)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "reports/opendata_327_submission_readiness_latest.json"
MERGE_LATEST = ROOT / "reports/opendata_327_pdf_merge_latest.json"
DEFAULT_OUT = ROOT / "reports/opendata_327_commander_handoff_latest.json"

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _kb(path: Path) -> float | None:
    if not path.is_file():
        return None
    return round(path.stat().st_size / 1024, 1)


def build() -> dict[str, Any]:
    readiness = {}
    if READINESS.is_file():
        readiness = json.loads(READINESS.read_text(encoding="utf-8-sig"))

    artifacts_table = [
        {
            "step": "게이트",
            "artifact": "G1(B/C/D) + G4",
            "status": "PASS" if readiness.get("pre_export_gates", {}).get("all_ok") else "check",
        },
        {
            "step": "Part B",
            "path": "reports/opendata_327_part_b_v1.pdf",
            "size_kb": _kb(ROOT / "reports/opendata_327_part_b_v1.pdf"),
        },
        {
            "step": "Part C",
            "path": "reports/opendata_327_part_c_draft_v1.pdf",
            "size_kb": _kb(ROOT / "reports/opendata_327_part_c_draft_v1.pdf"),
        },
        {
            "step": "Part D (Annex)",
            "path": "reports/opendata_327_part_d_annex_v1.pdf",
            "size_kb": _kb(ROOT / "reports/opendata_327_part_d_annex_v1.pdf"),
        },
        {
            "step": "병합 PDF (B+C+D)",
            "path": "reports/opendata_327_submission_bcd_merged_v1.pdf",
            "size_kb": _kb(ROOT / "reports/opendata_327_submission_bcd_merged_v1.pdf"),
            "note": "표지 A 없음 — step_4_merge bcd_merged_no_cover_a",
        },
    ]

    merge_doc: dict[str, Any] = {}
    if MERGE_LATEST.is_file():
        merge_doc = json.loads(MERGE_LATEST.read_text(encoding="utf-8-sig"))
    final_path = merge_doc.get("final_upload_pdf")
    cover_merged = bool(readiness.get("cover_a_merged")) or bool(final_path)
    if cover_merged and final_path:
        artifacts_table.append(
            {
                "step": "최종 업로드용 (A+B+C+D)",
                "path": final_path,
                "size_kb": _kb(ROOT / final_path),
                "note": "merge --cover-pdf 완료",
            }
        )
    else:
        artifacts_table.append(
            {
                "step": "최종 업로드용 (표지 A 후)",
                "path": None,
                "status": "pending",
                "note": "py scripts/merge_opendata_327_submission_pdf_v1.py --cover-pdf <cover_a.pdf>",
            }
        )

    human_only = [
        {
            "id": 1,
            "task": "opendata_327_submission_bcd_merged_v1.pdf 육안 검수 (§4-1·레이아웃)",
            "owner": "human",
        },
        {
            "id": 2,
            "task": "K-Startup 표지(A) 맨 앞 삽입",
            "owner": "human",
            "automation": "py scripts/merge_opendata_327_submission_pdf_v1.py --cover-pdf <path/to/cover_a.pdf>",
        },
        {
            "id": 3,
            "task": "§2-2 성능 목표 수치 내부 확정 → MD 수정 → Run-OpenData327SubmissionPrep_v1.ps1 재실행",
            "owner": "human",
        },
        {
            "id": 4,
            "task": "6/1 K-Startup dry-run",
            "owner": "human",
            "date_kst": "2026-06-01",
        },
    ]

    return {
        "schema": "opendata_327_commander_handoff_v1",
        "generated_at_utc": _utc_now(),
        "git_head_short": _git_head(),
        "legal_entity": readiness.get("legal_entity", "주식회사 목소리네트워크"),
        "technical_ready_for_pdf_bundle": readiness.get("technical_ready_for_pdf_bundle", False),
        "ready_for_kstartup_upload": readiness.get("ready_for_kstartup_upload", False),
        "execution_results_table": artifacts_table,
        "workflow_step_status": readiness.get("pre_export_gates", {}).get("workflow"),
        "human_only": human_only,
        "rerun_one_liner": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Run-OpenData327SubmissionPrep_v1.ps1",
        "rerun_chain_legacy": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Run-OpenData327SubmissionChain_v1.ps1",
        "readiness_pointer": READINESS.relative_to(ROOT).as_posix(),
        "boundary_ack": "PDF/BCD merge automated; cover insert remains human.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
