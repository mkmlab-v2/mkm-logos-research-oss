#!/usr/bin/env python3
"""Build NON_GATING 63779 pattern registry from observed data."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SIGNAL = ART / "chronicle_history_news_signal_stub_latest.json"
DEFAULT_HISTORY = ART / "chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ART / "logos_63779_registry_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _monthly_returns(csv_path: Path) -> list[float]:
    if not csv_path.is_file():
        return []
    rows: list[tuple[str, float]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = str(row.get("Date") or "")[:7]
            try:
                c = float(row.get("Close"))
            except (TypeError, ValueError):
                continue
            if d:
                rows.append((d, c))
    by_month: dict[str, list[float]] = {}
    for d, c in rows:
        by_month.setdefault(d, []).append(c)
    rets: list[float] = []
    for _, seq in sorted(by_month.items()):
        if len(seq) < 2 or seq[0] <= 0:
            continue
        rets.append((seq[-1] / seq[0] - 1.0) * 100.0)
    return rets


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def build_registry(signal: dict[str, Any], history_rows: list[dict[str, Any]], monthly_rets: list[float]) -> dict[str, Any]:
    signal_score = float((signal.get("signal_assessment") or {}).get("composite_signal_score") or 0.0)
    history_similarity = float((signal.get("history_pattern") or {}).get("similarity_score") or 0.0)
    coverage = float((signal.get("news_context") or {}).get("coverage_score") or 0.0)
    source_rel = float((signal.get("news_context") or {}).get("source_reliability_score") or 0.0)
    stress = float((signal.get("context_metrics") or {}).get("stress_index") or 0.0)
    regime = str((signal.get("context_metrics") or {}).get("dual_regime_primary_id") or "unknown")
    final_decision = str((signal.get("decision_layer") or {}).get("final_decision") or "WATCH")

    if history_rows:
        last = history_rows[-1]
        hist_signal = float(last.get("composite_signal_score") or signal_score)
        hist_similarity_tail = float(last.get("history_similarity") or history_similarity)
    else:
        hist_signal = signal_score
        hist_similarity_tail = history_similarity

    if monthly_rets:
        tail = monthly_rets[-6:]
        abs_avg = sum(abs(x) for x in tail) / len(tail)
        up_ratio = sum(1 for x in tail if x > 0) / len(tail)
    else:
        abs_avg = 0.0
        up_ratio = 0.5

    # 63779 as pattern-ID only (NON_GATING). Similarity is based on observed structure.
    similarity_63779 = _clip01(
        0.38 * history_similarity
        + 0.2 * hist_similarity_tail
        + 0.18 * _clip01(abs_avg / 12.0)
        + 0.14 * coverage
        + 0.1 * _clip01(1.0 - stress / 2.0)
    )

    cohesion_ratio = max(0.0, (hist_signal + signal_score + coverage) / 0.3)
    if cohesion_ratio < 1.0:
        cohesion_band = "<1x"
    elif cohesion_ratio < 3.0:
        cohesion_band = "1-3x"
    elif cohesion_ratio < 10.0:
        cohesion_band = "3-10x"
    else:
        cohesion_band = "10x+"

    chaos_score = _clip01((stress * 0.45) + ((1.0 - source_rel) * 0.35) + (_clip01(abs_avg / 15.0) * 0.2))
    order_score = _clip01((coverage * 0.4) + (source_rel * 0.35) + (_clip01(up_ratio) * 0.25))
    tension_score = _clip01((chaos_score * 0.55) + ((1.0 - order_score) * 0.45))
    phase_label = "chaos_tilt" if chaos_score > order_score + 0.08 else "order_tilt" if order_score > chaos_score + 0.08 else "balanced_tension"

    return {
        "schema": "logos_63779_registry_v1",
        "generated_at_utc": _now(),
        "source_refs": {
            "chronicle_signal_json": "docs/final/artifacts/chronicle_history_news_signal_stub_latest.json",
            "chronicle_history_jsonl": "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl",
            "market_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
        "pattern_id": "63779_like_v1",
        "regime_context": {"primary_regime": regime, "final_decision": final_decision},
        "deep_logos_tension_gematria": {
            "pattern_id": "63779_like_v1",
            "similarity_0_1": round(similarity_63779, 6),
            "cohesion_ratio": round(cohesion_ratio, 6),
            "cohesion_band": cohesion_band,
            "signal_score": round(signal_score, 6),
            "history_similarity": round(history_similarity, 6),
            "history_similarity_tail": round(hist_similarity_tail, 6),
            "price_mapping_forbidden": True,
            "non_gating_only": True,
            "falsification_conditions": [
                "similarity_0_1 < 0.20 for 3 consecutive updates",
                "coverage_score < 0.15 while source_reliability_score < 0.15",
            ],
        },
        "archetypal_chaos_order_phase": {
            "phase_label": phase_label,
            "chaos_score": round(chaos_score, 6),
            "order_score": round(order_score, 6),
            "tension_score": round(tension_score, 6),
            "narrative_claim": "질서/혼돈 해석은 시장 의미망 해설용이며 실행 트리거가 아니다.",
            "falsification_conditions": [
                "chaos_score and order_score both < 0.2",
                "tension_score swings >0.7 without matching signal/history evidence",
            ],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chronicle-signal-json", type=Path, default=DEFAULT_SIGNAL)
    ap.add_argument("--chronicle-history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--market-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    signal_path = args.chronicle_signal_json if args.chronicle_signal_json.is_absolute() else ROOT / args.chronicle_signal_json
    history_path = args.chronicle_history_jsonl if args.chronicle_history_jsonl.is_absolute() else ROOT / args.chronicle_history_jsonl
    market_path = args.market_csv if args.market_csv.is_absolute() else ROOT / args.market_csv
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not signal_path.is_file():
        raise SystemExit(f"Missing --chronicle-signal-json: {signal_path}")

    signal = _read_json(signal_path)
    history_rows = _read_jsonl(history_path)
    monthly_rets = _monthly_returns(market_path)
    payload = build_registry(signal, history_rows, monthly_rets)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pattern_id": payload["pattern_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

