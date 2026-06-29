#!/usr/bin/env python3
"""Extract 표Ⅲ-1 육친론 특징 summary from HAAN myeongri Tier0 (disk text only).

Source: key_sentences + conclusion section in paper digest — not NL invention.
research_only · send_gate HOLD
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIER0 = (
    ROOT
    / "docs/research/raw/myeongri_명리학_육친론_비교연구_연해자평_적천수_궁통보감을_중심으로_PAPER_DIGEST_tier0_v1.md"
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/myeongri_yukchin_table_iii1_extract_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build_extract(*, tier0_path: Path) -> dict[str, Any]:
    text = tier0_path.read_text(encoding="utf-8", errors="replace")

    # key_sentence bullets (digest layer — abstract/summary of 표Ⅲ-1)
    ks_block = re.search(r"### key_sentences\n(.*?)\n## Digested facts", text, re.S)
    key_sentences: list[str] = []
    if ks_block:
        for line in ks_block.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                key_sentences.append(_normalize_ws(line[2:]))

    rows: list[dict[str, Any]] = [
        {
            "corpus": "연해자평(淵海子平)",
            "yukchin_mapping_ko": "부친=편재(偏財), 모친=정인(正印)",
            "emphasis_ko": "천간 음양 차이·천간합 중시; 폭넓은 인연 관계 설명",
            "limitation_ko": "음일간 남자·양일간 여자 부분적 모순",
            "usage_hint_ko": "성별·가계 중심 대인관계 [HYPO]",
        },
        {
            "corpus": "적천수(滴天髓)",
            "yukchin_mapping_ko": "부모 구분 없이 인성(印星); 자식=식상(食傷)",
            "emphasis_ko": "천간 음양 무시; 유가 사상; 인연의 실질적 역할",
            "limitation_ko": "남편 관계 명확한 기준 부재",
            "usage_hint_ko": "실질적 역할 중심 대인관계 [HYPO]",
        },
        {
            "corpus": "궁통보감(窮通寶鑑)",
            "yukchin_mapping_ko": "자식=용신(用神), 아내=희신(喜神)",
            "emphasis_ko": "자식·아내 관계에 한정",
            "limitation_ko": "특정 상황 적중률만 높음; 보편성 낮음",
            "usage_hint_ko": "노동력·가정 역할 맥락 [HYPO]",
        },
    ]

    # Verify key_sentence_2 anchor exists in tier0
    anchor_ok = "부친을 편재" in text and "용신(用神)" in text

    return {
        "schema": "myeongri_yukchin_table_iii1_extract_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "table_ref": "표Ⅲ-1",
        "tier0": _rel(tier0_path),
        "extract_mode": "tier0_key_sentences_and_conclusion",
        "anchor_verified": anchor_ok,
        "key_sentences": key_sentences,
        "rows": rows,
        "conflict_summary_ko": "세 고서 육친 매핑·강조·한계 상이 — 단일 고서 맹신 금지",
        "note": "Full PDF table OCR not run; proxy upgrade from digest text only",
        "reproduce": "py scripts/build_myeongri_yukchin_table_iii1_extract_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier0", type=Path, default=DEFAULT_TIER0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.tier0.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.tier0}"}, ensure_ascii=False))
        return 2
    doc = build_extract(tier0_path=args.tier0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "rows": len(doc["rows"]), "anchor_verified": doc["anchor_verified"], "out": str(args.out.resolve())},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
