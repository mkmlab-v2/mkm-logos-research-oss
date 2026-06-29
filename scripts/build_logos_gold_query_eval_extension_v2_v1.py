#!/usr/bin/env python3
"""Build gold extension v2: holdout paraphrases q25-q48 from existing q01-q24 [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_OUT = ROOT / "docs/final/fixtures/logos_gold_query_eval_extension_v2.json"

HOLDOUT_QUERIES: dict[str, tuple[str, str]] = {
    "q01": ("q25", "위기 속에서도 언약과 신실하심이 유지되는 성경 경로는?"),
    "q02": ("q26", "무너짐 직전의 경고와 심판 신호는 어디서 드러나는가?"),
    "q03": ("q27", "심판 경고와 회복 약속이 동시에 나타나는 경로는?"),
    "q04": ("q28", "심판 이후에도 남는 언약 잔류의 논증 경로는?"),
    "q05": ("q29", "hubris·trade 붕괴와 변동성 쇼크를 잇는 Logos 대응 경로는?"),
    "q06": ("q30", "십자가에서 흘린 물과 피의 상징을 연결하는 구절 경로는?"),
    "q07": ("q31", "언약 안에서 사랑과 용서가 연결되는 경로는?"),
    "q08": ("q32", "고난 중 위로가 함께하는 성경 패턴 경로는?"),
    "q09": ("q33", "선거·전환기 공동체 경계와 시대 분별 경로는?"),
    "q10": ("q34", "야간 변동성 충격 속 위로와 견고함 경로는?"),
    "q11": ("q35", "WATCH 구간에서 경계와 분별의 성경 경로는?"),
    "q12": ("q36", "Dan 2 왕국 전환 상징과 궁정 위기 경로는?"),
    "q13": ("q37", "수난 중 물·피 상징의 성경 연결 경로는?"),
    "q14": ("q38", "장기 압박 속 소망 징표의 성경 경로는?"),
    "q15": ("q39", "유동성 압박 속 신중함과 대비의 경로는?"),
    "q16": ("q40", "혼란 이후 긍휴·자비가 드러나는 경로는?"),
    "q17": ("q41", "인프라 복원력 은유의 성경 연결 경로는?"),
    "q18": ("q42", "반도체 공급망·단단한 재료의 성경 경로는?"),
    "q19": ("q43", "불확실성 속 지혜·분별의 경로는?"),
    "q20": ("q44", "디지털 신뢰·진실성의 성경 경로는?"),
    "q21": ("q45", "변동성 속 절제·인내의 경로는?"),
    "q22": ("q46", "capitulation 이후 회복·소망 경로는?"),
    "q23": ("q47", "다니엘 2 아람어 궁정·왕의 꿈 경로는?"),
    "q24": ("q48", "배신·음모 속 깨어 있음과 경계 경로는?"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_extension_v2(gold_path: Path) -> dict[str, Any]:
    gold = json.loads(gold_path.read_text(encoding="utf-8-sig"))
    by_id = {str(x.get("id")): x for x in (gold.get("items") or []) if isinstance(x, dict)}
    items: list[dict[str, Any]] = []
    for src_id, (new_id, query_ko) in HOLDOUT_QUERIES.items():
        src = by_id.get(src_id)
        if not src:
            continue
        item = {k: v for k, v in src.items() if k not in ("id", "query_ko", "notes_ko", "promotion_signoff_utc")}
        item["id"] = new_id
        item["query_ko"] = query_ko
        item["holdout_source_id"] = src_id
        item["eval_tier"] = "gold_required"
        item["notes_ko"] = f"[HYPO] holdout paraphrase of {src_id}; anti-overfit split."
        items.append(item)
    return {
        "schema": "logos_gold_query_eval_extension_v2",
        "version": "1.0.0",
        "target_gold_version": "1.2.0",
        "hypothesis_tier": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_extension_v2(args.gold_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "items": len(doc["items"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
