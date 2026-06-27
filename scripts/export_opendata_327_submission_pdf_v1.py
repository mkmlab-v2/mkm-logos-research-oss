#!/usr/bin/env python3
"""Regenerate OpenData 327 Part B/C HTML and PDF via headless Edge/Chrome."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MERGE_GUIDE = ROOT / "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.json"
REPORTS = ROOT / "reports"
GATES_LATEST = REPORTS / "opendata_327_pre_export_gates_latest.json"

STRIP_HEADINGS = ("(부록) 우선 준비", "변경 이력")
STRIP_LINE_PATTERNS = (
    r"^-\s+\*\*schema:",
    r"^-\s+\*\*용도:",
    r"^-\s+\*\*전체 로드맵:",
    r"^-\s+\*\*과제 상세:",
    r"^-\s+\*\*Fact-Lock:",
    r"`docs/",
    r"`reports/",
    r"moksori_mega_commercialization",
    r"mkmlife",
    r"연계 로드맵",
    r"범위 주의",
    r"^-\s+\*\*연계",
    r"^-\s+\*\*범위",
    r"a-codeai\.com",
    r"P0_COMMERCIALIZATION",
    r"MKM_DOMAIN_PORTFOLIO",
    r"PERSONADIARY",
    r"AGENTS\.md",
    r"붙여 넣기용",
    r"붙여넣기용",
)

NEXT_HUMAN_KO = [
    "K-Startup 표지(A) 양식 수동 병합 + Annex(D) 선택",
    "§2-2 목표안 수치는 제출 전 내부 벤치로 확정",
    "K-Startup + 나라장터 접수 (6/5 18:00)",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _find_browser() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("Edge/Chrome not found for headless PDF export")


def _strip_md(text: str) -> str:
    lines: list[str] = []
    skip = False
    for line in text.splitlines():
        if any(h in line for h in STRIP_HEADINGS):
            skip = True
            continue
        if skip and line.startswith("## ") and not any(h in line for h in STRIP_HEADINGS):
            skip = False
        if skip:
            continue
        if "제출 시 삭제" in line or "파란색 안내" in line:
            continue
        if any(re.search(p, line) for p in STRIP_LINE_PATTERNS):
            continue
        if line.strip().startswith("※"):
            continue
        if "Phase 2" in line and "B2B" in line:
            continue
        lines.append(line)
    out = "\n".join(lines).strip()
    out = re.sub(r"^#{1,6}\s+", "", out, flags=re.MULTILINE)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"`([^`]+)`", r"\1", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def _md_to_html(md_text: str, title: str) -> str:
    body = html.escape(md_text)
    return (
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        f"<title>{html.escape(title)}</title></head><body>"
        '<pre style="white-space:pre-wrap;font-family:Malgun Gothic,Segoe UI,sans-serif;'
        f'font-size:11pt;line-height:1.45">{body}</pre></body></html>'
    )


def _print_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    uri = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        uri,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f"PDF export failed exit={proc.returncode} stderr={proc.stderr[:500]!r}"
        )


def _refresh_gates_workflow(*, export_doc: dict[str, Any]) -> None:
    """Merge PDF export paths into gates JSON (UTF-8; avoids PowerShell encoding bugs)."""
    if GATES_LATEST.is_file():
        gates = json.loads(GATES_LATEST.read_text(encoding="utf-8-sig"))
    else:
        gates = {"schema": "opendata_327_pre_export_gates_v1", "gates": [], "all_gates_ok_for_export_draft": True}

    parts = export_doc.get("parts") or []
    part_b = next((p for p in parts if "part_b" in str(p.get("pdf", ""))), {})
    part_c = next((p for p in parts if "part_c" in str(p.get("pdf", ""))), {})
    part_d = next((p for p in parts if "part_d" in str(p.get("pdf", ""))), {})
    part_b_pdf = part_b.get("pdf")
    size_mb = (
        round((ROOT / part_b_pdf).stat().st_size / (1024 * 1024), 2) if part_b_pdf else 0.0
    )

    gates["generated_at_utc"] = _utc_now()
    gates["workflow_step_status"] = {
        "step_1_strip_md": "completed",
        "step_2_fill_placeholders": "completed_draft_targets",
        "step_3_export_pdf": "completed",
        "step_4_merge": "b_only_interim_no_cover_a",
        "step_5_size_check": "ok_under_30mb" if size_mb < 30 else "over_30mb_review",
        "step_6_kstartup_dry_run": "scheduled_2026-06-01",
        "step_7_final_submit": "scheduled_2026-06-04_05",
    }
    gates["export_artifacts"] = {
        "part_b_pdf": part_b.get("pdf"),
        "part_b_pdf_merge_name": export_doc.get("part_b_pdf_merge_name"),
        "part_c_pdf": part_c.get("pdf"),
        "part_d_pdf": part_d.get("pdf"),
        "part_b_html": part_b.get("html"),
        "part_c_html": part_c.get("html"),
        "part_d_html": part_d.get("html"),
        "part_b_size_mb": size_mb,
    }
    gates["merge_guide"] = "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.md"
    gates["next_human"] = list(NEXT_HUMAN_KO)
    GATES_LATEST.parent.mkdir(parents=True, exist_ok=True)
    GATES_LATEST.write_text(json.dumps(gates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _export_part(
    *,
    browser: Path,
    source_md: Path,
    html_out: Path,
    pdf_out: Path,
    title: str,
) -> dict[str, Any]:
    md = _strip_md(source_md.read_text(encoding="utf-8"))
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(_md_to_html(md, title), encoding="utf-8")
    _print_pdf(browser, html_out, pdf_out)
    size_kb = round(pdf_out.stat().st_size / 1024, 1)
    return {
        "source_md": source_md.relative_to(ROOT).as_posix(),
        "html": html_out.relative_to(ROOT).as_posix(),
        "pdf": pdf_out.relative_to(ROOT).as_posix(),
        "size_kb": size_kb,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-part-c", action="store_true")
    ap.add_argument("--skip-part-d", action="store_true")
    args = ap.parse_args()

    guide = json.loads(MERGE_GUIDE.read_text(encoding="utf-8"))
    part_b_md = ROOT / guide["merge_order"][1]["source_md"]
    part_c_md = ROOT / guide["merge_order"][2]["source_md"]
    part_d_md = ROOT / guide["merge_order"][3]["source_md"]

    browser = _find_browser()
    out: dict[str, Any] = {
        "schema": "opendata_327_pdf_export_v1",
        "generated_at_utc": _utc_now(),
        "browser": browser.name,
        "parts": [],
    }

    out["parts"].append(
        _export_part(
            browser=browser,
            source_md=part_b_md,
            html_out=REPORTS / "opendata_327_part_b_draft_v1.html",
            pdf_out=REPORTS / "opendata_327_part_b_v1.pdf",
            title="OpenData 327 Part B",
        )
    )
    merge_pdf = REPORTS / guide["output_target"]["filename_suggestion"]
    shutil.copy2(REPORTS / "opendata_327_part_b_v1.pdf", merge_pdf)
    out["part_b_pdf_merge_name"] = merge_pdf.relative_to(ROOT).as_posix()

    if not args.skip_part_c:
        out["parts"].append(
            _export_part(
                browser=browser,
                source_md=part_c_md,
                html_out=REPORTS / "opendata_327_part_c_draft_v1.html",
                pdf_out=REPORTS / "opendata_327_part_c_draft_v1.pdf",
                title="OpenData 327 Part C",
            )
        )

    if not args.skip_part_d and part_d_md.is_file():
        out["parts"].append(
            _export_part(
                browser=browser,
                source_md=part_d_md,
                html_out=REPORTS / "opendata_327_part_d_annex_v1.html",
                pdf_out=REPORTS / "opendata_327_part_d_annex_v1.pdf",
                title="OpenData 327 Part D Annex",
            )
        )

    summary_path = REPORTS / "opendata_327_pdf_export_latest.json"
    summary_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _refresh_gates_workflow(export_doc=out)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(summary_path),
                "gates": str(GATES_LATEST),
                "parts": out["parts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
