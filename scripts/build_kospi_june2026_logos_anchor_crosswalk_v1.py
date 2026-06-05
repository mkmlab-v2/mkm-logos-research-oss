#!/usr/bin/env python3
"""KOSPI June 2026 × Logos GraphRAG anchor crosswalk [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KOSPI = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_GRAPHRAG = ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json"

MONTH_TOPIC_PRIORS: list[dict[str, Any]] = [
    {
        "topic_id": "election_20260603",
        "weight": 0.9,
        "rationale_ko": "6월 초 대선·정치 이벤트 달력 [HYPO]",
        "active_dates_prefix": ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"],
    },
    {
        "topic_id": "regime_watch_lehman_shadow",
        "weight": 0.85,
        "rationale_ko": "보고서 status=WATCH·channel_anchor 혼재 [HYPO][NON_GATING]",
        "trigger": "watch_or_anchor",
    },
    {
        "topic_id": "ai_hubris_trade",
        "weight": 0.7,
        "rationale_ko": "상승 우세·AI/거시 내러티브 오버레이 [HYPO]",
        "trigger": "bull_majority",
    },
    {
        "topic_id": "excess_unwind",
        "weight": 0.55,
        "rationale_ko": "중순 이후 조정·만기 이벤트 보조 [HYPO]",
        "active_dates_contains": ["06-11"],
    },
    {
        "topic_id": "risk_off_overnight",
        "weight": 0.4,
        "rationale_ko": "WATCH·야간 risk-off 보조 [HYPO][NON_GATING]",
        "trigger": "watch_or_overnight_aux",
    },
]


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _topic_index(topics_doc: dict[str, Any], graphrag_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gr_by = {t["topic_id"]: t for t in graphrag_doc.get("topics") or [] if t.get("topic_id")}
    out: dict[str, dict[str, Any]] = {}
    for t in topics_doc.get("topics") or []:
        tid = str(t.get("topic_id") or "")
        gr = gr_by.get(tid) or {}
        out[tid] = {
            "topic_id": tid,
            "seed_verse_ids": list(t.get("seed_verse_ids") or []),
            "graphrag_ref": t.get("graphrag_ref"),
            "seed_router_overlap": list(gr.get("seed_router_overlap") or []),
            "seed_hit_count": gr.get("seed_hit_count"),
        }
    return out


def _select_month_topics(kospi: dict[str, Any]) -> list[dict[str, Any]]:
    ex = kospi.get("executive_summary_ko") or {}
    status = str(kospi.get("status") or "")
    bull = int(ex.get("bull_days") or 0)
    bear = int(ex.get("bear_days") or 0)
    anchor_days = int(ex.get("channel_anchor_days") or 0)
    rows = kospi.get("rows") or []
    date_strings = [
        str(r.get("session_date") or r.get("date") or r.get("trading_date") or "")
        for r in rows
        if isinstance(r, dict)
    ]

    selected: list[dict[str, Any]] = []
    for prior in MONTH_TOPIC_PRIORS:
        tid = str(prior["topic_id"])
        ok = False
        trigger = prior.get("trigger")
        if trigger == "watch_or_anchor" and (status == "WATCH" or anchor_days > 0):
            ok = True
        elif trigger == "bull_majority" and bull > bear:
            ok = True
        elif trigger == "watch_or_overnight_aux" and (status == "WATCH" or bear > 0):
            ok = True
        elif trigger == "bear_days_positive" and bear > 0:
            ok = True
        prefixes = prior.get("active_dates_prefix") or []
        if prefixes and any(any(d.startswith(p) for p in prefixes) for d in date_strings):
            ok = True
        contains = prior.get("active_dates_contains") or []
        if contains and any(any(c in d for c in contains) for d in date_strings):
            ok = True
        if ok:
            selected.append(
                {
                    "topic_id": tid,
                    "weight": prior["weight"],
                    "rationale_ko": prior["rationale_ko"],
                }
            )
    selected.sort(key=lambda x: float(x["weight"]), reverse=True)
    return selected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-json", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--graphrag-json", type=Path, default=DEFAULT_GRAPHRAG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    kospi = _read(args.kospi_json)
    topics_doc = _read(args.topics_json)
    graphrag_doc = _read(args.graphrag_json)
    if not kospi:
        print(json.dumps({"ok": False, "error": f"missing kospi: {args.kospi_json}"}))
        return 2

    topic_idx = _topic_index(topics_doc, graphrag_doc)
    month_topics = _select_month_topics(kospi)
    anchors = []
    for mt in month_topics:
        tid = mt["topic_id"]
        meta = topic_idx.get(tid) or {}
        anchors.append(
            {
                **mt,
                "seed_verse_ids": meta.get("seed_verse_ids") or [],
                "graphrag_ref": meta.get("graphrag_ref"),
                "router_overlap": meta.get("seed_router_overlap") or [],
                "router_coverage": f"{meta.get('seed_hit_count') or 0}/{len(meta.get('seed_verse_ids') or [])}",
                "logos_role": "[NON_GATING] narrative anchor only",
            }
        )

    ex = kospi.get("executive_summary_ko") or {}
    doc = {
        "schema": "kospi_june2026_logos_anchor_crosswalk_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_wall": "no_track_a_live_auto_merge",
        "kospi_source": str(args.kospi_json.relative_to(ROOT)).replace("\\", "/"),
        "kospi_status": kospi.get("status"),
        "kospi_stance_ko": ex.get("stance"),
        "summary": {
            "topics_linked": len(anchors),
            "primary_topic": anchors[0]["topic_id"] if anchors else None,
            "graphrag_seed_hits_ssot": (graphrag_doc.get("summary") or {}).get("seed_hits"),
        },
        "interpretation_guard": "Logos anchors are interpretive crosswalk — not price triggers.",
        "anchors": anchors,
        "field_lens_order": "Field(regime) → Lens(Logos[NON_GATING]) → Conflict → Final Action(HOLD/WATCH)",
        "final_action_hint": "WATCH",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "topics_linked": len(anchors), "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
