#!/usr/bin/env python3
"""Logos exploration closure → insight digest for showroom/narrative [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_exploration_insight_digest_v1_latest.json"

POINTERS = {
    "closure": ROOT / "reports/logos_4d_ann_exploration_closure_v1_latest.json",
    "gold_eval": ROOT / "reports/logos_gold_query_eval_v1_latest.json",
    "graphrag": ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json",
    "alternate": ROOT / "reports/logos_4d_vs_alternate_retrieval_v1_latest.json",
    "promotion": ROOT / "reports/logos_regime_watch_luke_promotion_verify_v1_latest.json",
    "wiring": ROOT / "reports/logos_gold_typology_rerank_wiring_v1_latest.json",
    "kospi_crosswalk": ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json",
}


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    closure = _read(POINTERS["closure"])
    gold = _read(POINTERS["gold_eval"])
    graphrag = _read(POINTERS["graphrag"])
    alternate = _read(POINTERS["alternate"])
    promotion = _read(POINTERS["promotion"])
    wiring = _read(POINTERS["wiring"])
    kospi = _read(POINTERS["kospi_crosswalk"])

    verdict = closure.get("verdict") or {}
    routing = closure.get("routing_policy") or {}
    bullets_ko = [
        f"GraphRAG seed 커버리지: {verdict.get('graphrag_topic_seed_retrieval', graphrag.get('summary', {}).get('seed_hits'))} [FACT]",
        f"Gold router eval: {(gold.get('summary') or {}).get('items_evaluated', '?')} items · "
        f"all_pass={(gold.get('summary') or {}).get('gold_required_all_pass')} [FACT]",
        f"4D organic spike: {verdict.get('organic_4d_topic_spike')} — centroid ANN 승격 게이트 아님 [FACT]",
        "primary=concept_bridge+GraphRAG+gold_eval; assist=typology+lemma; demote=4D organic [FACT]",
        "성경(Logos) 렌즈는 [NON_GATING] 해설·앵커만 — 실매매·Track A 자동 합선 없음 [HYPO]",
    ]
    if kospi.get("anchors"):
        primary = (kospi.get("summary") or {}).get("primary_topic")
        bullets_ko.append(f"KOSPI 6월 crosswalk primary Logos topic: {primary} [HYPO]")

    doc = {
        "schema": "logos_exploration_insight_digest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": closure.get("final_action") or "HOLD_EXPLORATION",
        "routing": {
            "primary": routing.get("primary_ssot"),
            "demote": routing.get("demote"),
            "recommendation": alternate.get("routing_recommendation"),
        },
        "gates": {
            "graphrag_seed_hits": (graphrag.get("summary") or {}).get("seed_hits"),
            "graphrag_topic_hits": (graphrag.get("summary") or {}).get("topic_hits"),
            "gold_required_all_pass": (gold.get("summary") or {}).get("gold_required_all_pass"),
            "typology_wiring_ok": (wiring.get("summary") or {}).get("wiring_ok"),
            "luke_promotion_ok": promotion.get("ok"),
            "organic_4d_topic_spike": verdict.get("organic_4d_topic_spike"),
        },
        "insight_bullets_ko": bullets_ko,
        "showroom_framing_ko": {
            "opening": "검증 가능한 경로(bridge·GraphRAG)와 gold CPU eval을 전면에 둡니다.",
            "limit": "4D centroid ANN organic spike는 연구 모니터링 전용이며 상용 승격 근거가 아닙니다.",
            "disclaimer": "[HYPO][NON_GATING] 해설 레이어 — 가격·주문 트리거 아님.",
        },
        "artifact_pointers": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in POINTERS.items()},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "final_action": doc["final_action"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
