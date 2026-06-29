#!/usr/bin/env python3
"""Build Han Vocology volume gap table vs A5 page targets."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research"
OUT_MD = RESEARCH / "HAN_VOCOLOGY_VOLUME_GAP_V0_1.md"
OUT_JSON = ROOT / "docs/final/artifacts/han_vocology_volume_gap_v1_latest.json"

CHARS_PER_PAGE_A5 = 1000  # mixed KR+table heuristic
TARGET_A5_MIN = 200
TARGET_A5_MAX = 350

A_VOL: list[tuple[str, str, float]] = [
    ("제1장", "HAN_VOCOLOGY_CH1_DEFINITION_V0_1.md", 18.0),
    ("제2장", "HAN_VOCOLOGY_CH2_ZANGFU_VOICE_V0_1.md", 22.0),
    ("제3장", "HAN_VOCOLOGY_CH3_MODERN_VOCAL_SCIENCE_V0_1.md", 24.0),
    ("제4장", "HAN_VOCOLOGY_CH4_SASANG_DIAGNOSIS_V0_1.md", 20.0),
    ("제5장", "HAN_VOCOLOGY_CH5_MODERN_ASSESSMENT_V0_1.md", 22.0),
    ("제6장", "HAN_VOCOLOGY_CH6_INTEGRATED_CASE_V0_1.md", 16.0),
    ("제7장", "HAN_VOCOLOGY_CH7_MTD_V0_1.md", 28.0),
    ("제8장", "HAN_VOCOLOGY_CH8_VOCAL_NODULES_V0_1.md", 20.0),
    ("제9장", "HAN_VOCOLOGY_CH9_SD_V0_1.md", 14.0),
    ("제10장", "HAN_VOCOLOGY_CH10_OTHER_DISORDERS_V0_1.md", 22.0),
    ("부록1·2", "HAN_VOCOLOGY_APPENDIX_1_2_TABLES_V0_1.md", 12.0),
    ("부록5", "HAN_VOCOLOGY_APPENDIX_5_MOLECULAR_V0_1.md", 8.0),
    ("부록6", "HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md", 6.0),
    ("부록7", "HAN_VOCOLOGY_APPENDIX_7_SELF_CARE_V0_1.md", 6.0),
    ("맺음말", "HAN_VOCOLOGY_CLOSING_AND_COURSE_SCRIPT_V0_1.md", 8.0),
    ("참고문헌", "HAN_VOCOLOGY_REFERENCES_V0_1.md", 6.0),
    ("케이스뱅크", "HAN_VOCOLOGY_CASE_BANK_V0_1.md", 14.0),
]

B_VOL: list[tuple[str, str, float]] = [
    ("발성오류10선", "HAN_VOCOLOGY_VOCAL_MYTHS_CORRECTION_10_V0_1.md", 24.0),
    ("부록3·4", "HAN_VOCOLOGY_APPENDIX_B_PRACTICE_V0_1.md", 32.0),
    ("부록7(재인용)", "HAN_VOCOLOGY_APPENDIX_7_SELF_CARE_V0_1.md", 6.0),
]

FIGURE_BUDGET_A = 12.0  # ~13 images in A export
FIGURE_BUDGET_B = 4.0


def _stats(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chars = len(re.sub(r"\s+", "", text))
    cjk = len(re.findall(r"[\u4e00-\u9fff\uac00-\ud7af]", text))
    tables = text.count("|---|")
    h2 = len(re.findall(r"^## ", text, re.M))
    h3 = len(re.findall(r"^### ", text, re.M))
    return {
        "lines_total": len(lines),
        "chars_no_ws": chars,
        "cjk_hangul": cjk,
        "tables": tables,
        "h2": h2,
        "h3": h3,
    }


def _est_pages(s: dict[str, Any]) -> float:
    base = s["chars_no_ws"] / CHARS_PER_PAGE_A5
    table_bonus = s["tables"] * 0.35
    return round(base + table_bonus, 1)


def _gap(actual: float, target: float) -> float:
    return round(target - actual, 1)


def _pct(actual: float, target: float) -> int:
    if target <= 0:
        return 0
    return int(round(100 * actual / target))


def _docx_paragraph_count(docx_path: Path) -> int | None:
    if not docx_path.is_file():
        return None
    try:
        from docx import Document  # type: ignore

        doc = Document(str(docx_path))
        return len(doc.paragraphs)
    except Exception:
        return None


def build() -> dict[str, Any]:
    rows_a: list[dict[str, Any]] = []
    for label, fname, target in A_VOL:
        path = RESEARCH / fname
        s = _stats(path)
        actual = _est_pages(s)
        rows_a.append(
            {
                "volume": "A",
                "label": label,
                "file": f"docs/research/{fname}",
                "version": "v0.2" if "v0.2" in path.read_text(encoding="utf-8")[:200] or fname.endswith("_V0_1.md") else "v0.1",
                "target_pages_a5": target,
                "actual_pages_est": actual,
                "gap_pages": _gap(actual, target),
                "fill_pct": _pct(actual, target),
                "chars_no_ws": s["chars_no_ws"],
                "tables": s["tables"],
                "status": "ok" if actual >= target * 0.85 else ("thin" if actual >= target * 0.5 else "critical"),
            }
        )

    rows_b: list[dict[str, Any]] = []
    for label, fname, target in B_VOL:
        path = RESEARCH / fname
        s = _stats(path)
        actual = _est_pages(s)
        rows_b.append(
            {
                "volume": "B",
                "label": label,
                "file": f"docs/research/{fname}",
                "target_pages_a5": target,
                "actual_pages_est": actual,
                "gap_pages": _gap(actual, target),
                "fill_pct": _pct(actual, target),
                "chars_no_ws": s["chars_no_ws"],
                "tables": s["tables"],
                "status": "ok" if actual >= target * 0.85 else ("thin" if actual >= target * 0.5 else "critical"),
            }
        )

    a_body = sum(r["actual_pages_est"] for r in rows_a)
    b_body = sum(r["actual_pages_est"] for r in rows_b)
    a_target = sum(t for _, _, t in A_VOL) + FIGURE_BUDGET_A
    b_target = sum(t for _, _, t in B_VOL) + FIGURE_BUDGET_B
    combined_actual = a_body + b_body + FIGURE_BUDGET_A + FIGURE_BUDGET_B
    combined_target_mid = (TARGET_A5_MIN + TARGET_A5_MAX) / 2

    docx_a = ROOT / "reports/han_vocology_export_volume_a_v0_1_latest.docx"
    docx_b = ROOT / "reports/han_vocology_export_volume_b_v0_1_latest.docx"

    return {
        "schema": "han_vocology_volume_gap_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "method": {
            "chars_per_page_a5": CHARS_PER_PAGE_A5,
            "note_ko": "MD 본문+표 휴리스틱; DOCX 인쇄 분량과 ±20% 오차 가능",
        },
        "targets": {
            "combined_a5_min": TARGET_A5_MIN,
            "combined_a5_max": TARGET_A5_MAX,
            "volume_a_target_incl_figures": a_target,
            "volume_b_target_incl_figures": b_target,
        },
        "summary": {
            "volume_a_body_pages_est": round(a_body, 1),
            "volume_a_total_est": round(a_body + FIGURE_BUDGET_A, 1),
            "volume_a_target": a_target,
            "volume_a_gap_to_target": round(a_target - (a_body + FIGURE_BUDGET_A), 1),
            "volume_b_body_pages_est": round(b_body, 1),
            "volume_b_total_est": round(b_body + FIGURE_BUDGET_B, 1),
            "volume_b_target": b_target,
            "volume_b_gap_to_target": round(b_target - (b_body + FIGURE_BUDGET_B), 1),
            "combined_total_est": round(combined_actual, 1),
            "combined_fill_pct_vs_200": _pct(combined_actual, TARGET_A5_MIN),
            "combined_fill_pct_vs_350": _pct(combined_actual, TARGET_A5_MAX),
            "combined_gap_to_mid_275": round(combined_target_mid - combined_actual, 1),
        },
        "docx_proxy": {
            "volume_a_paragraphs": _docx_paragraph_count(docx_a),
            "volume_b_paragraphs": _docx_paragraph_count(docx_b),
            "volume_a_images": 13,
            "volume_b_images": 3,
        },
        "chapters": rows_a + rows_b,
        "priority_gaps": sorted(
            [r for r in rows_a + rows_b if r["gap_pages"] > 0],
            key=lambda x: x["gap_pages"],
            reverse=True,
        )[:8],
        "blocked_figures": [
            {
                "fig_id": "F05-A",
                "reason": "strobe clinical chart blocked_license — use F05-B schematic",
                "substitute": "F05 han_vocology_fig05_strobe_interpret_schematic_v1_latest.png",
            }
        ],
    }


def _md_table(rows: list[dict[str, Any]], vol: str) -> str:
    lines = [
        f"### {vol}권 장별",
        "",
        "| 장 | 목표p | 현재p(est) | gap | 충족% | 상태 |",
        "|----|-------|------------|-----|-------|------|",
    ]
    for r in rows:
        if r["volume"] != vol:
            continue
        lines.append(
            f"| {r['label']} | {r['target_pages_a5']} | {r['actual_pages_est']} | "
            f"{r['gap_pages']} | {r['fill_pct']}% | {r['status']} |"
        )
    return "\n".join(lines)


def write_md(data: dict[str, Any]) -> None:
    s = data["summary"]
    pri = data["priority_gaps"]
    lines = [
        "# 한의음성학 분량 Gap 표 v0.1",
        "",
        "**Status:** `[B-track · 교재 기획]` · `send_gate: HOLD`",
        f"**Generated:** {data['generated_at_utc']}",
        f"**SSOT JSON:** `docs/final/artifacts/han_vocology_volume_gap_v1_latest.json`",
        "",
        f"> **측정:** MD `chars_no_ws` ÷ {CHARS_PER_PAGE_A5} + 표 보너스. A5 인쇄 확정 전 **휴리스틱**.",
        "",
        "## 요약",
        "",
        f"| 지표 | 값 |",
        f"|------|-----|",
        f"| **합산 현재(est)** | **{s['combined_total_est']}p** (A {s['volume_a_total_est']} + B {s['volume_b_total_est']}) |",
        f"| 목표 범위 | {TARGET_A5_MIN}–{TARGET_A5_MAX}p (A5) |",
        f"| 200p 대비 | {s['combined_fill_pct_vs_200']}% |",
        f"| 350p 대비 | {s['combined_fill_pct_vs_350']}% |",
        f"| 중간값(275p) gap | **{s['combined_gap_to_mid_275']}p** 부족 |",
        f"| A권 gap (목표 {data['targets']['volume_a_target_incl_figures']}p) | {s['volume_a_gap_to_target']}p |",
        f"| B권 gap (목표 {data['targets']['volume_b_target_incl_figures']}p) | {s['volume_b_gap_to_target']}p |",
        "",
        "## 상태 범례",
        "",
        "| status | 의미 |",
        "|--------|------|",
        "| ok | 목표 85%+ |",
        "| thin | 50–85% |",
        "| critical | 50% 미만 |",
        "",
        _md_table(data["chapters"], "A"),
        "",
        _md_table(data["chapters"], "B"),
        "",
        "## 우선 확장 Top 8 (gap 큰 순)",
        "",
        "| 순위 | 장 | gap(p) | 제안 |",
        "|------|-----|--------|------|",
    ]
    for i, r in enumerate(pri, 1):
        suggest = {
            "제2장": "장부별 사례음·침예 2건/장부",
            "제3장": "strobe·acoustic 해석 연습 4건",
            "제7장": "protocol 주차별 SOAP·VT 시트",
            "발성오류10선": "항목별 5분 영상 스크립트",
            "부록3·4": "질환별 12주 VT 일지",
            "제4장": "사상별 케이스 2건",
            "제5장": "검사 판독 워크시트",
            "제10장": "LPR·presbyphonia 케이스 각 1건",
        }.get(r["label"], "케이스·실습표 추가")
        lines.append(f"| {i} | {r['label']} | {r['gap_pages']} | {suggest} |")

    lines += [
        "",
        "## 도판·차단",
        "",
        "| fig | 상태 | gap 영향 |",
        "|-----|------|----------|",
        "| F01–F04,F07–F15 | rendered | 반영됨 |",
        "| F12 | adjudicated_education_internal | 반영 |",
        "| **F05-B** | **rendered_schematic_substitute** | 반영 (캡처 대체) |",
        "| F05-A | blocked_license (clinical chart) | 출판 시 별도 인용 |",
        "",
        "## 재현",
        "",
        "```bash",
        "py scripts/build_han_vocology_volume_gap_v1.py",
        "```",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    data = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_md(data)
    print(json.dumps({"ok": True, "combined_est": data["summary"]["combined_total_est"], "out": str(OUT_JSON)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
