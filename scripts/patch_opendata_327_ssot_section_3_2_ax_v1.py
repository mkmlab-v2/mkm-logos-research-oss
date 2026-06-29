#!/usr/bin/env python3
"""Idempotent §3-2 AX cost-governance paragraph — no Track A / 47% / WSE-3 (OpenData 327)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OVERVIEW = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md"
SUBMISSION_B = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"
PART_C = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_submission_v1.md"

MARKER = "비용·품질 거버넌스"

AX_PARAGRAPH = (
    "**AX 비용·품질 거버넌스 (2026 맥락)**  \n"
    "2026년 기업 AX 도입에서는 API 호출량·컨텍스트 길이에 따른 **비용 통제**가 핵심 리스크로 부상하고 있다. "
    "본 과제는 범용 챗봇형 사용량 경쟁이 아니라, **공고·서식 근거 RAG**, **슬롯 기반 생성**, "
    "**근거 미연결 시 HOLD**, **감사 가능 로그**로 **추론 호출 상한과 품질을 동시에** 관리하는 "
    "**비용·품질 거버넌스**를 목표로 한다. "
    "(내부 연구용 토큰·압축 벤치마크는 **본 공모 범위와 데이터를 합선하지 않는다**.)"
)

PART_C_BULLET = (
    "- **AX 비용 통제(과제 범위):** 공고·서식 RAG·슬롯·HOLD·감사 로그로 **추론 상한·품질**을 함께 관리한다. "
    "내부 토큰·압축 벤치마크는 **본 공모 데이터·주장과 합선하지 않는다**."
)

ANCHOR_OVERVIEW = (
    "(범용 상용 압축 API·타 도메인 KPI와 **합선하지 않음**)."
)
INSERT_AFTER_OVERVIEW = f"{ANCHOR_OVERVIEW}\n\n{AX_PARAGRAPH}\n"

ANCHOR_PART_C = "**시장성**  \n"
INSERT_AFTER_PART_C = f"{ANCHOR_PART_C}\n{PART_C_BULLET}\n"


def _patch_overview_like(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False, "already_present"
    if ANCHOR_OVERVIEW not in text:
        return False, "anchor_not_found"
    path.write_text(text.replace(ANCHOR_OVERVIEW, INSERT_AFTER_OVERVIEW, 1), encoding="utf-8")
    return True, "patched"


def _patch_part_c(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    text = path.read_text(encoding="utf-8")
    if PART_C_BULLET.split("**AX 비용")[0] in text and MARKER in text:
        return False, "already_present"
    if ANCHOR_PART_C not in text:
        return False, "anchor_not_found"
    path.write_text(text.replace(ANCHOR_PART_C, INSERT_AFTER_PART_C, 1), encoding="utf-8")
    return True, "patched"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/opendata_327_section_3_2_ax_patch_latest.json")
    args = ap.parse_args()

    results: dict[str, str] = {}
    for label, path, fn in (
        ("overview", OVERVIEW, _patch_overview_like),
        ("submission_b", SUBMISSION_B, _patch_overview_like),
        ("part_c", PART_C, _patch_part_c),
    ):
        if args.dry_run:
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            results[label] = "would_patch" if MARKER not in text and path.is_file() else "skip"
        else:
            ok, status = fn(path)
            results[label] = status if ok or status in ("already_present", "missing") else status

    doc = {
        "schema": "opendata_327_section_3_2_ax_patch_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": args.dry_run,
        "marker": MARKER,
        "results": results,
    }
    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
