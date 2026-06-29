#!/usr/bin/env python3
"""Extract 수요기업 과제소개서 (별첨1 PDF) section for OI collab task SSOT."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Downloads" / "(별첨1) 수요기업 과제소개서.pdf"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json"
META_OUT = ROOT / "reports/kstartup_open_innovation_20460237_demand_intro_extract_latest.json"

COLLAB_DEMAND_COMPANY = "한국평가데이터"
TASK_MARKER = "AI 기반 RPA를 활용한 수작업 업무 프로세스 자동화"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_spaces(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_footer(text: str) -> str:
    text = re.sub(r"\s*-\s*\d+\s*-\s*\d*\s*$", "", text)
    return _normalize_spaces(text)


def _pdf_text(pdf_path: Path) -> str:
    import fitz  # noqa: PLC0415

    doc = fitz.open(str(pdf_path))
    return "\n".join(doc.load_page(i).get_text() for i in range(doc.page_count))


def _between_markers(text: str, start: str, end: str | None) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    chunk = text[i:]
    if end:
        j = chunk.find(end, len(start))
        if j > 0:
            chunk = chunk[:j]
    return chunk.strip()


def _bullet_block(section: str, label: str) -> str:
    m = re.search(rf"◦\({re.escape(label)}\)(.*?)(?=◦\(|< 참여|$)", section, re.S)
    if not m:
        return ""
    raw = m.group(1)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _requirements(section: str) -> list[str]:
    m = re.search(r"◦\(요구사항\)(.*?)< 참여", section, re.S)
    if not m:
        return []
    block = m.group(1)
    block = re.sub(r"-\s*\d+\s*-", "", block)  # page footers like "- 18 -"
    raw_items = re.split(r"\n\s*-\s*", "\n" + block)
    items: list[str] = []
    for chunk in raw_items:
        chunk = re.sub(r"\s+", " ", chunk).strip()
        if not chunk or re.fullmatch(r"\d+", chunk):
            continue
        items.append(chunk)
    return items


def _criteria(section: str) -> list[str]:
    m = re.search(r"< 참여 스타트업의 기준요건 및 권장사항 >(.*?)◦\(활용계획\)", section, re.S)
    if not m:
        return []
    block = m.group(1)
    items = re.findall(r"▪\s*([^\n▪]+)", block)
    return [_normalize_spaces(x) for x in items if x.strip()]


def extract(pdf_path: Path) -> dict:
    text = _pdf_text(pdf_path)
    section = _between_markers(
        text,
        TASK_MARKER,
        "한국플랜트서비스 과제소개서",
    )
    if not section:
        raise SystemExit(f"task section not found in PDF: {TASK_MARKER}")

    subtitle_m = re.search(r"▸\s*([^\n]+)", section)
    subtitle = subtitle_m.group(1).strip() if subtitle_m else ""

    return {
        "schema": "kstartup_oi_demand_task_intro_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "source_pdf": str(pdf_path),
        "demand_company": COLLAB_DEMAND_COMPANY,
        "strategy_field": "AI",
        "strategy_detail": "AI 에이전트",
        "task_title": TASK_MARKER,
        "task_subtitle": subtitle,
        "situation": _clean_footer(_bullet_block(section, "현황")),
        "problem": _clean_footer(_bullet_block(section, "문제점")),
        "requirements": _requirements(section),
        "startup_criteria": _criteria(section),
        "utilization_plan": _clean_footer(_bullet_block(section, "활용계획")),
        "collab_support": _clean_footer(_bullet_block(section, "협업지원")),
        "raw_section_chars": len(section),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta", type=Path, default=META_OUT)
    ap.add_argument("--txt-out", type=Path, default=ROOT / "reports/kstartup_open_innovation_20460237_demand_korea_eval_rpa_intro_v1.txt")
    args = ap.parse_args()

    if not args.pdf.is_file():
        raise SystemExit(f"PDF missing: {args.pdf}")

    data = extract(args.pdf.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    txt_lines = [
        f"수요기업: {data['demand_company']}",
        f"과제: {data['task_title']}",
        f"세부: {data['task_subtitle']}",
        "",
        "[현황]",
        data["situation"],
        "",
        "[문제점]",
        data["problem"],
        "",
        "[요구사항]",
        *[f"- {x}" for x in data["requirements"]],
        "",
        "[참여 스타트업 기준요건]",
        *[f"- {x}" for x in data["startup_criteria"]],
        "",
        "[활용계획]",
        data["utilization_plan"],
        "",
        "[협업지원]",
        data["collab_support"],
    ]
    args.txt_out.parent.mkdir(parents=True, exist_ok=True)
    args.txt_out.write_text("\n".join(txt_lines).strip() + "\n", encoding="utf-8")

    meta = {
        "ok": True,
        "schema": "kstartup_oi_demand_task_intro_extract_v1",
        "generated_at_utc": data["generated_at_utc"],
        "json_out": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "txt_out": str(args.txt_out.relative_to(ROOT)).replace("\\", "/"),
        "requirements_count": len(data["requirements"]),
        "criteria_count": len(data["startup_criteria"]),
    }
    args.meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
