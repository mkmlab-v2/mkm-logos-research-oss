#!/usr/bin/env python3
"""Build B-track chronicle-history-news signal (observation only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def _candidate_decision(score: float, thresholds: dict[str, Any]) -> str:
    reduce_min = float(thresholds.get("reduce_min", 0.7))
    watch_min = float(thresholds.get("watch_min", 0.35))
    if score >= reduce_min:
        return "REDUCE"
    if score >= watch_min:
        return "WATCH"
    return "HOLD"


def _regime_metrics(regime_map: dict[str, Any]) -> tuple[str, float]:
    regimes = regime_map.get("regimes")
    if not isinstance(regimes, dict) or not regimes:
        return "unknown", 0.35
    best_id = "unknown"
    best_entries = -1
    non_unknown = 0
    for rid, body in regimes.items():
        if not isinstance(body, dict):
            continue
        n_entries = int(body.get("n_entries", 0) or 0)
        if rid != "unknown" and n_entries > 0:
            non_unknown += 1
        if n_entries > best_entries:
            best_entries = n_entries
            best_id = str(rid)
    # In bootstrap maps often n_entries are 0; keep conservative baseline.
    confidence = 0.35 if non_unknown == 0 else _clamp01(0.35 + min(non_unknown, 4) * 0.1)
    return best_id, confidence


def _news_metrics(news_rows: list[dict[str, Any]], lookback_days: int = 7) -> tuple[float, float, float, int]:
    now = _now_utc()
    cutoff = now - timedelta(days=lookback_days)
    window = []
    for r in news_rows:
        as_of = r.get("as_of_utc")
        try:
            dt = datetime.fromisoformat(str(as_of).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            window.append(r)
    if not window:
        return 0.2, 0.2, 0.2, 0

    coverage_score = _clamp01(len(window) / 20.0)
    non_hypo = sum(1 for r in window if str(r.get("hypothesis_tag", "")).strip() != "[HYPO]")
    source_reliability = _clamp01(0.2 + (non_hypo / len(window)) * 0.8)
    risk_terms = ("widen", "volatility", "risk-off", "stress", "shock")
    risk_hits = 0
    for r in window:
        txt = str(r.get("canonical_text", "")).lower()
        if any(t in txt for t in risk_terms):
            risk_hits += 1
    context_stress_inverse = _clamp01(1.0 - (risk_hits / len(window)))
    return coverage_score, source_reliability, context_stress_inverse, len(window)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_rules = root / "docs" / "final" / "artifacts" / "chronicle_history_news_decision_rules_v1.json"
    default_out = root / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_stub_latest.json"
    default_regime = root / "data" / "regimes" / "regime_map.json"
    default_news = root / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"
    default_history = root / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_history_latest.jsonl"

    ap = argparse.ArgumentParser(description="Build chronicle-history-news signal stub (B-track).")
    ap.add_argument("--rules-json", default=str(default_rules))
    ap.add_argument("--output-json", default=str(default_out))
    ap.add_argument("--regime-map-json", default=str(default_regime))
    ap.add_argument("--news-jsonl", default=str(default_news))
    ap.add_argument("--history-jsonl", default=str(default_history))
    args = ap.parse_args()

    now = _now_utc()
    rules = _load_json(Path(args.rules_json))
    weights = rules.get("score_weights", {})
    thresholds = rules.get("thresholds", {})
    policy = rules.get("decision_policy", {})

    regime_map = _load_json(Path(args.regime_map_json))
    news_rows = _load_jsonl(Path(args.news_jsonl))

    dual_regime_primary_id, history_similarity = _regime_metrics(regime_map)
    coverage_score, source_reliability, context_stress_inverse, window_count = _news_metrics(news_rows, lookback_days=7)

    composite = (
        float(weights.get("history_similarity", 0.45)) * history_similarity
        + float(weights.get("news_reliability_adjusted", 0.35)) * source_reliability
        + float(weights.get("context_stress_inverse", 0.2)) * context_stress_inverse
    )
    composite = max(0.0, min(1.0, composite))
    cand = _candidate_decision(composite, thresholds)

    # B-track guard: keep observation-only and conservative final.
    final_decision = "HOLD" if policy.get("most_conservative_wins", True) else cand

    doc = {
        "schema": "chronicle_history_news_signal_v1",
        "generated_at_utc": _iso(now),
        "governance_state": "S1_SHADOW",
        "source_track": "B",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "chronicle_window": {
            "window_id": f"chronicle_{now.strftime('%Y%m%d')}_d7",
            "start_utc": _iso(now - timedelta(days=7)),
            "end_utc": _iso(now),
            "granularity": "daily"
        },
        "history_pattern": {
            "pattern_id": "historical_regime_echo_stub_v1",
            "similarity_score": round(history_similarity, 6),
            "evidence_refs": [
                "data/regimes/regime_map.json",
                "docs/final/artifacts/global_atom_corpus_fact_brief_latest.md"
            ]
        },
        "news_context": {
            "news_window_id": f"news_{now.strftime('%Y%m%d')}_d7",
            "coverage_score": round(coverage_score, 6),
            "source_reliability_score": round(source_reliability, 6),
            "noise_penalty": round(max(0.0, 1.0 - source_reliability), 6)
        },
        "context_metrics": {
            "dual_regime_primary_id": dual_regime_primary_id,
            "dual_regime_confidence": round(history_similarity, 6),
            "stress_index": round(max(0.0, 1.0 - context_stress_inverse), 6)
        },
        "signal_assessment": {
            "composite_signal_score": round(composite, 6),
            "signal_quality": "medium" if composite >= 0.35 else "low",
            "notes": [
                "B-track observation-only signal",
                "Not auto-bound to A-track triggers"
            ]
        },
        "decision_layer": {
            "candidate_decision": cand,
            "most_conservative_wins": True,
            "final_decision": final_decision,
            "auto_bind_to_atrack_forbidden": True,
            "decision_reason": "Conservative override under S1_SHADOW/KEEP_OBSERVATION_ONLY"
        }
    }

    out_path = Path(args.output_json)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history_path = Path(args.history_jsonl)
    history_row = {
        "schema": "chronicle_history_news_signal_history_row_v1",
        "generated_at_utc": _iso(now),
        "source_track": "B",
        "governance_state": "S1_SHADOW",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "dual_regime_primary_id": dual_regime_primary_id,
        "window_count": window_count,
        "history_similarity": round(history_similarity, 6),
        "source_reliability_score": round(source_reliability, 6),
        "context_stress_inverse": round(context_stress_inverse, 6),
        "composite_signal_score": round(composite, 6),
        "candidate_decision": cand,
        "final_decision": final_decision,
    }
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history_row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "schema": "chronicle_history_news_signal_build_v1",
                "output_json": str(out_path),
                "history_jsonl": str(history_path),
                "composite_signal_score": round(composite, 6),
                "candidate_decision": cand,
                "final_decision": final_decision,
                "window_count": window_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
