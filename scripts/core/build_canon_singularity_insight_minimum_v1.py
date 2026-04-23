#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _clean_text(s: str) -> str:
    return " ".join(str(s).split())


def _token_diversity(text: str) -> float:
    toks = [t for t in text.split(" ") if t]
    if not toks:
        return 0.0
    return len(set(toks)) / len(toks)


def _regime_note(regime: str) -> str:
    notes = {
        "bull_pump": "상승 가속 국면과의 정렬 강도가 높은 행입니다.",
        "sideways_accumulation": "횡보-축적 국면과의 정렬이 반복적으로 관찰됩니다.",
        "bear_trend": "하락 추세 국면과의 정렬 가능성이 상대적으로 높습니다.",
        "capitulation": "투매/항복 국면과의 정렬 신호가 두드러집니다.",
    }
    return notes.get(regime, "기본 레짐 정렬 신호가 관찰됩니다.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build minimum canon insight brief from canon lane summary.")
    ap.add_argument(
        "--summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json",
    )
    ap.add_argument("--top-n", type=int, default=12)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_v1.json",
    )
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    args = ap.parse_args()

    data = _read_json(Path(args.summary_json))
    rows = list(data.get("top_canon_global") or [])
    for row in rows:
        text_preview = _clean_text(str(row.get("text_preview") or ""))
        row["_token_diversity"] = _token_diversity(text_preview)
        row["_clean_text_preview"] = text_preview
    rows = sorted(
        rows,
        key=lambda r: (
            float(r.get("score", 0.0)),
            float(r.get("margin_vs_second", 0.0)),
            float(r.get("_token_diversity", 0.0)),
            str(r.get("row_id") or ""),
        ),
        reverse=True,
    )
    top = rows[: int(args.top_n)]
    insights: list[dict[str, Any]] = []
    regime_counts: dict[str, int] = {}
    for idx, row in enumerate(top, start=1):
        regime = str(row.get("best_regime") or "unknown")
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
        score = float(row.get("score", 0.0))
        margin = float(row.get("margin_vs_second", 0.0))
        text_preview = str(row.get("_clean_text_preview") or "")
        token_div = float(row.get("_token_diversity", 0.0))
        commentary = (
            f"{row.get('row_id')}는 {regime} 정렬 점수 {score:.6f}, "
            f"2순위 대비 마진 {margin:.6f}로 분리되며, {_regime_note(regime)}"
        )
        insights.append(
            {
                "rank": idx,
                "row_id": row.get("row_id"),
                "best_regime": regime,
                "score": score,
                "margin_vs_second": margin,
                "state16": row.get("state16"),
                "text_preview": text_preview,
                "token_diversity": round(token_div, 6),
                "commentary": commentary,
                "evidence": {
                    "source_summary": str(args.summary_json),
                    "source_fields": [
                        "row_id",
                        "best_regime",
                        "score",
                        "margin_vs_second",
                        "state16",
                        "text_preview",
                    ],
                },
            }
        )

    dominant_regime = None
    if regime_counts:
        dominant_regime = max(regime_counts.items(), key=lambda x: x[1])[0]

    out = {
        "schema": "original_corpus_regime_singularity_canon_insight_minimum_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "summary_json": str(args.summary_json),
            "top_n": int(args.top_n),
        },
        "counts": {
            "insight_rows": len(insights),
            "regime_counts": regime_counts,
        },
        "meta": {
            "dominant_regime_in_top_n": dominant_regime,
            "method": "Template-based minimum insight from canon lane summary.",
            "rank_policy_version": "score_margin_tokendiv_v2",
            "rank_policy": [
                "score desc",
                "margin_vs_second desc",
                "token_diversity desc",
                "row_id desc",
            ],
        },
        "insights": insights,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_jsonl(
        Path(args.history_jsonl),
        {
            "schema": "original_corpus_regime_singularity_canon_insight_minimum_event_v1",
            "generated_at_utc": out["generated_at_utc"],
            "inputs": out["inputs"],
            "counts": out["counts"],
            "meta": out["meta"],
            "insights": out["insights"],
        },
    )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

