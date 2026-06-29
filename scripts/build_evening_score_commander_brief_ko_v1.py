#!/usr/bin/env python3
"""Build plain-KO commander brief from evening_multi_lens_score_v1 [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "evening_multi_lens_score_v1.json"
DEFAULT_OUT = ROOT / "reports" / "evening_score_commander_brief_ko_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_brief(score: dict) -> dict:
    rows = list(score.get("prediction_scores") or [])
    ma = score.get("multi_asset") or {}
    sm = score.get("summary") or {}

    directional = [r for r in rows if r.get("price_axis") in ("HIT", "FAIL", "NEUTRAL_DRAW")]
    graphrag_rows = [r for r in rows if r.get("kind") == "graphrag_path_hit"]
    graphrag_fail = [r for r in graphrag_rows if r.get("outcome") == "FAIL"]
    graphrag_hit = [r for r in graphrag_rows if r.get("outcome") == "HIT"]
    ref_only = [r for r in rows if r.get("price_axis") == "REFERENCE_ONLY"]
    structural_hit = [r for r in rows if r.get("price_axis") == "N/A" and r.get("outcome") == "HIT"]

    kospi = ma.get("kospi") or {}
    btc = ma.get("btc") or {}
    nasdaq = ma.get("nasdaq") or {}

    hits = [r for r in directional if r.get("price_axis") == "HIT"]
    fails = [r for r in directional if r.get("price_axis") == "FAIL"]
    neutral = [r for r in directional if r.get("price_axis") == "NEUTRAL_DRAW"]

    plain_lines = [
        f"봉인 seal={score.get('seal_id')} · 총 {sm.get('n_predictions')}건 중 "
        f"가격축 채점 가능 {len(directional)}건 → soft_hit≈{sm.get('price_soft_hit_rate')} "
        f"(HIT {len(hits)} · FAIL {len(fails)} · NEUTRAL {len(neutral)}).",
        f"당일 KOSPI 종가 방향: {kospi.get('direction')} ({kospi.get('return_pct')}%). "
        f"BTC 저녁창: {btc.get('direction')}. NASDAQ: {nasdaq.get('note') or nasdaq.get('direction')}.",
        (
            f"Logos GraphRAG {len(graphrag_rows)}건: 구조 HIT {len(graphrag_hit)} · FAIL {len(graphrag_fail)} "
            f"(가격축 N/A — 종가 방향 채점과 별도)."
            if graphrag_rows
            else "Logos GraphRAG: 해당 없음."
        ),
        (
            "사상(sasang) 1건 KOSPI 상승일과 방향 일치(HIT). "
            "명리·가격 B-track 방향 가설은 상승일 대비 bear/불일치."
            if hits
            else "가격축 HIT 없음 — 방향 가설 전반 재검토 [HYPO]."
        ),
        "Track A·실매매·go_no_go 자동 반영 금지 — evolution 제안은 human sign-off 전 rules 변경 없음.",
    ]

    return {
        "schema": "evening_score_commander_brief_ko_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "source": str(DEFAULT_IN.relative_to(ROOT)).replace("\\", "/"),
        "calendar_kst": score.get("calendar_kst"),
        "seal_id": score.get("seal_id"),
        "market_close": {
            "kospi": kospi,
            "btc": btc,
            "nasdaq": nasdaq,
        },
        "summary_price_axis": sm,
        "plain_ko": plain_lines,
        "directional_hits": [
            {
                "prediction_id": r.get("prediction_id"),
                "lens": r.get("lens"),
                "kind": r.get("kind"),
                "note": r.get("note"),
            }
            for r in hits
        ],
        "directional_fails": [
            {
                "prediction_id": r.get("prediction_id"),
                "lens": r.get("lens"),
                "kind": r.get("kind"),
                "note": r.get("note"),
                "market_direction": r.get("market_direction"),
            }
            for r in fails
        ],
        "directional_neutral": [
            {
                "prediction_id": r.get("prediction_id"),
                "lens": r.get("lens"),
                "kind": r.get("kind"),
                "note": r.get("note"),
            }
            for r in neutral
        ],
        "not_market_direction_miss": {
            "graphrag_path_hit_count": len(graphrag_rows),
            "graphrag_path_hit_hit_count": len(graphrag_hit),
            "graphrag_path_hit_fail_count": len(graphrag_fail),
            "graphrag_note_ko": "subgraph replay 구조 채점 — 종가 방향 채점 아님(price_axis=N/A)",
            "reference_only_count": len(ref_only),
            "structural_hit_count": len(structural_hit),
            "structural_hit_note_ko": "gold eval 등 구조 통과 — 가격 단정 아님",
        },
        "stats_by_lens": score.get("stats_by_lens"),
        "telegram_one_liner_ko": (
            f"🌙 R-IBL {score.get('calendar_kst')} seal={score.get('seal_id')[:8]}… "
            f"KOSPI {kospi.get('direction')} {kospi.get('return_pct')}% · "
            f"가격축 soft={sm.get('price_soft_hit_rate')} "
            f"(H{sm.get('price_axis_HIT')}/F{sm.get('price_axis_FAIL')}/N{sm.get('price_axis_NEUTRAL_DRAW')}) "
            f"[HYPO]"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-json", default=str(DEFAULT_IN))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    inp = Path(args.in_json)
    if not inp.is_file():
        print(json.dumps({"error": f"missing {inp}"}, ensure_ascii=False))
        return 2

    score = json.loads(inp.read_text(encoding="utf-8-sig"))
    doc = build_brief(score)
    out = Path(args.out_json)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "seal_id": doc.get("seal_id")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
