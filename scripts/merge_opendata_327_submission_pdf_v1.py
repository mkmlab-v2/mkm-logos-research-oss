#!/usr/bin/env python3
"""Merge OpenData 327 Part B (+ optional C, D) PDFs. Cover (A) remains manual."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
GATES_LATEST = REPORTS / "opendata_327_pre_export_gates_latest.json"
MERGE_GUIDE = ROOT / "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.json"
DEFAULT_OUT = REPORTS / "opendata_327_submission_bcd_merged_v1.pdf"
FINAL_WITH_COVER = REPORTS / "moksori_ai_opendata327_task1_business_plan_v1.pdf"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _merge_pdfs(paths: list[Path], out_path: Path) -> dict[str, Any]:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    pages = 0
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"missing PDF: {path}")
        reader = PdfReader(str(path))
        writer.append(reader)
        pages += len(reader.pages)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        writer.write(fh)
    size_mb = round(out_path.stat().st_size / (1024 * 1024), 2)
    return {"pages_appended": pages, "size_mb": size_mb, "parts": [p.relative_to(ROOT).as_posix() for p in paths]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-pdf", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-part-c", action="store_true")
    ap.add_argument("--skip-part-d", action="store_true")
    ap.add_argument("--no-gates-update", action="store_true")
    ap.add_argument(
        "--cover-pdf",
        type=Path,
        default=None,
        help="K-Startup cover (Part A) PDF — prepended to produce final upload file",
    )
    ap.add_argument(
        "--final-out-pdf",
        type=Path,
        default=FINAL_WITH_COVER,
        help="Output when --cover-pdf is set (default: moksori_ai_opendata327_task1_business_plan_v1.pdf)",
    )
    args = ap.parse_args()

    part_b = REPORTS / "opendata_327_part_b_v1.pdf"
    part_c = REPORTS / "opendata_327_part_c_draft_v1.pdf"
    part_d = REPORTS / "opendata_327_part_d_annex_v1.pdf"

    ordered = [part_b]
    if not args.skip_part_c:
        ordered.append(part_c)
    if not args.skip_part_d:
        ordered.append(part_d)

    result = _merge_pdfs(ordered, args.out_pdf)
    cover_a: str | None = None
    final_pdf: str | None = None
    if args.cover_pdf is not None:
        if not args.cover_pdf.is_file():
            raise FileNotFoundError(f"cover PDF not found: {args.cover_pdf}")
        final_result = _merge_pdfs([args.cover_pdf, args.out_pdf], args.final_out_pdf)
        cover_a = args.cover_pdf.relative_to(ROOT).as_posix()
        final_pdf = args.final_out_pdf.relative_to(ROOT).as_posix()
        step_4 = "abcd_merged_with_cover_a"
    else:
        step_4 = "bcd_merged_no_cover_a"

    doc = {
        "schema": "opendata_327_pdf_merge_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "output_pdf": args.out_pdf.relative_to(ROOT).as_posix(),
        "cover_part_a": cover_a or "manual_kstartup_form_required",
        "final_upload_pdf": final_pdf,
        "merge_order": result["parts"],
        "size_mb": result["size_mb"],
        "final_size_mb": (
            round(args.final_out_pdf.stat().st_size / (1024 * 1024), 2) if final_pdf else None
        ),
        "max_size_mb": 30,
        "under_size_limit": result["size_mb"] < 30,
        "boundary_ack": (
            "Final upload PDF includes cover A."
            if final_pdf
            else "Merged B(+C+D) only. Insert K-Startup cover (A) before upload."
        ),
    }
    summary = REPORTS / "opendata_327_pdf_merge_latest.json"
    summary.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_gates_update and GATES_LATEST.is_file():
        gates = json.loads(GATES_LATEST.read_text(encoding="utf-8-sig"))
        gates["generated_at_utc"] = _utc_now()
        ws = gates.setdefault("workflow_step_status", {})
        ws["step_4_merge"] = step_4
        size_check = doc["final_size_mb"] if final_pdf else doc["size_mb"]
        ws["step_5_size_check"] = "ok_under_30mb" if size_check and size_check < 30 else "over_30mb_review"
        ea = gates.setdefault("export_artifacts", {})
        ea["bcd_merged_pdf"] = doc["output_pdf"]
        ea["bcd_merged_size_mb"] = doc["size_mb"]
        if final_pdf:
            ea["final_upload_pdf"] = final_pdf
            ea["final_upload_size_mb"] = doc["final_size_mb"]
        gates["next_human"] = (
            [
                "K-Startup + 나라장터 접수 (6/5 18:00)",
                "§2-2 목표안 수치는 제출 전 내부 벤치로 확정",
            ]
            if final_pdf
            else [
                "K-Startup 표지(A)를 맨 앞에 수동 삽입 후 업로드",
                "§2-2 목표안 수치는 제출 전 내부 벤치로 확정",
                "K-Startup + 나라장터 접수 (6/5 18:00)",
            ]
        )
        GATES_LATEST.write_text(json.dumps(gates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "output": doc["output_pdf"], "size_mb": doc["size_mb"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
