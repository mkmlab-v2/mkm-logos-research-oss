#!/usr/bin/env python3
"""OpenData 327 submission readiness — gates, PDF artifacts, human remainder (local)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / "reports/opendata_327_pre_export_gates_latest.json"
EXPORT = ROOT / "reports/opendata_327_pdf_export_latest.json"
MERGE_LATEST = ROOT / "reports/opendata_327_pdf_merge_latest.json"
HANDOFF = ROOT / "reports/opendata_327_commander_handoff_latest.json"
PART_B_MD = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"
CHECKLIST = ROOT / "docs/final/artifacts/opendata_327_kstartup_submission_checklist_v1_latest.json"
PARALLEL = ROOT / "docs/final/artifacts/opendata_327_parallel_lane_checklist_v1_latest.json"
MERGE_GUIDE = ROOT / "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.md"
DEFAULT_OUT = ROOT / "reports/opendata_327_submission_readiness_latest.json"

DEADLINE_KST = datetime(2026, 6, 5, 18, 0, 0)  # noqa: DTZ001 — label anchor only


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _file_meta(rel: str | None) -> dict[str, Any]:
    if not rel:
        return {"path": None, "exists": False}
    p = ROOT / rel.replace("/", "\\") if "\\" not in rel else ROOT / rel
    if not p.is_file():
        return {"path": rel, "exists": False}
    size_mb = round(p.stat().st_size / (1024 * 1024), 3)
    return {
        "path": rel,
        "exists": True,
        "size_mb": size_mb,
        "under_30mb": size_mb < 30,
    }


def _section_2_2_note(md_path: Path) -> dict[str, Any]:
    if not md_path.is_file():
        return {"ok": False, "note": "part_b_md_missing"}
    text = md_path.read_text(encoding="utf-8")
    block = ""
    if "### 2-2." in text:
        block = text.split("### 2-2.", 1)[1].split("\n## ", 1)[0]
    bracket_lines = [
        ln.strip()
        for ln in block.splitlines()
        if re.search(r"\[\s*\]", ln) and "|" not in ln
    ]
    return {
        "ok": True,
        "has_draft_bracket_note": "유지 가능" in block or "[ ]" in block,
        "table_has_target_numbers": "≥" in block or "목표안" in block,
        "human_confirm_before_submit": True,
        "bracket_only_lines": bracket_lines[:5],
    }


def build() -> dict[str, Any]:
    gates = _load(GATES) or {}
    export = _load(EXPORT) or {}
    checklist = _load(CHECKLIST) or {}
    gates_ok = bool(gates.get("all_gates_ok_for_export_draft"))
    part_b_pdf = (export.get("part_b_pdf_merge_name") or "reports/moksori_ai_opendata327_task1_business_plan_v1.pdf")
    part_b = _file_meta(export.get("parts", [{}])[0].get("pdf") if export.get("parts") else None)
    merge = _file_meta(part_b_pdf)
    part_c_pdf = None
    if export.get("parts") and len(export["parts"]) > 1:
        part_c_pdf = export["parts"][1].get("pdf")
    part_c = _file_meta(part_c_pdf)
    part_d_pdf = None
    if export.get("parts") and len(export["parts"]) > 2:
        part_d_pdf = export["parts"][2].get("pdf")
    part_d = _file_meta(part_d_pdf)

    merge_bcd = _load(MERGE_LATEST) or {}
    bcd_merged = _file_meta(merge_bcd.get("output_pdf"))
    final_upload = _file_meta(merge_bcd.get("final_upload_pdf"))
    has_cover = bool(merge_bcd.get("final_upload_pdf"))

    technical_ready = (
        gates_ok
        and merge.get("exists")
        and merge.get("under_30mb", False)
        and bcd_merged.get("exists", False)
    )
    human_items = list(gates.get("next_human") or [])
    for g in checklist.get("pre_submit_gates") or []:
        if g.get("done") is None and g.get("owner") == "human":
            human_items.append(f"{g.get('id')}: {g.get('check')}")

    return {
        "schema": "opendata_327_submission_readiness_v1",
        "generated_at_utc": _utc_now(),
        "legal_entity": checklist.get("legal_entity", {}).get("name", "주식회사 목소리네트워크"),
        "deadline_kst": checklist.get("deadline", {}).get("kst", "2026-06-05T18:00:00+09:00"),
        "technical_ready_for_pdf_bundle": technical_ready,
        "ready_for_kstartup_upload": False,
        "ready_for_kstartup_upload_blockers": (
            ["G3/G4/G5 human gates in kstartup checklist"]
            if has_cover
            else [
                "표지(A) 수동 병합 미완료",
                "G3/G4/G5 human gates in kstartup checklist",
            ]
        ),
        "cover_a_merged": has_cover,
        "pre_export_gates": {
            "all_ok": gates_ok,
            "pointer": GATES.relative_to(ROOT).as_posix(),
            "workflow": gates.get("workflow_step_status"),
        },
        "artifacts": {
            "part_b_pdf": part_b,
            "merge_pdf": merge,
            "part_c_pdf": part_c,
            "part_d_annex_pdf": part_d,
            "bcd_merged_pdf": bcd_merged,
            "final_upload_pdf": final_upload,
            "export_summary": EXPORT.relative_to(ROOT).as_posix() if EXPORT.is_file() else None,
            "merge_summary": MERGE_LATEST.relative_to(ROOT).as_posix() if MERGE_LATEST.is_file() else None,
        },
        "section_4_1_in_submission_md": True,
        "section_2_2": _section_2_2_note(PART_B_MD),
        "human_next": human_items,
        "pointers": {
            "merge_guide": MERGE_GUIDE.relative_to(ROOT).as_posix(),
            "kstartup_checklist": CHECKLIST.relative_to(ROOT).as_posix(),
            "parallel_lane": PARALLEL.relative_to(ROOT).as_posix(),
            "chain_script": "scripts/Run-OpenData327SubmissionChain_v1.ps1",
            "prep_script": "scripts/Run-OpenData327SubmissionPrep_v1.ps1",
            "handoff_script": "scripts/build_opendata_327_commander_handoff_v1.py",
            "commander_handoff": HANDOFF.relative_to(ROOT).as_posix(),
        },
        "track_wall": "separate_from_LG_compression_OEM",
        "boundary_ack": "technical_ready does not imply legal sign-off or K-Startup submit complete.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh-parallel-checklist", action="store_true")
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.refresh_parallel_checklist and PARALLEL.is_file():
        parallel = json.loads(PARALLEL.read_text(encoding="utf-8-sig"))
        parallel["last_pdf_export_utc"] = doc["generated_at_utc"]
        parallel["pre_export_gates_pointer"] = doc["pre_export_gates"]["pointer"]
        parallel["pdf_export_pointer"] = doc["artifacts"]["merge_pdf"].get("path")
        parallel["submission_readiness_pointer"] = args.out_json.relative_to(ROOT).as_posix()
        parallel["section_4_1_in_submission_md"] = doc["section_4_1_in_submission_md"]
        PARALLEL.write_text(json.dumps(parallel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "technical_ready": doc["technical_ready_for_pdf_bundle"],
                "output": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
