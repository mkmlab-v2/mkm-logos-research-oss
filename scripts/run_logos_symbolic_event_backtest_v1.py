#!/usr/bin/env python3
"""Backtest news->Logos symbolic mapping against walk-forward direction labels.

Research-only B-track utility:
- maps canonical_text keywords to symbolic events
- converts symbol scores to a directional call (up/down/neutral)
- joins each news row to first future direction label (strict PIT)
- reports hit-rate, chronology-aware symbolic inference, and split metrics
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "tests" / "fixtures" / "news_observation_v1.sample.jsonl"
DEFAULT_LABELS = ROOT / "tests" / "fixtures" / "join_walkforward_smoke_v1.labels.jsonl"
DEFAULT_SYMBOL_MAP = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_map_v1.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_OUT_CSV = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_rows_latest.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _parse_as_of_date_utc(as_of_utc: str) -> date:
    s = str(as_of_utc).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _parse_label_date(s: str) -> date:
    y, m, d = [int(x) for x in str(s).strip().split("-")]
    return date(y, m, d)


def _normalize_label_direction(value: str) -> str:
    v = str(value or "").strip().lower()
    if v in {"up", "bull", "long"}:
        return "up"
    if v in {"down", "bear", "short"}:
        return "down"
    return "neutral"


def _regime_multiplier(as_of_date: date, symbol_map: dict[str, Any]) -> float:
    windows = symbol_map.get("chronology_windows")
    if not isinstance(windows, list):
        return 1.0
    for w in windows:
        if not isinstance(w, dict):
            continue
        try:
            start = _parse_label_date(str(w.get("start_date") or "1900-01-01"))
            end = _parse_label_date(str(w.get("end_date") or "2999-12-31"))
        except Exception:
            continue
        if start <= as_of_date <= end:
            try:
                return float(w.get("score_multiplier") or 1.0)
            except (TypeError, ValueError):
                return 1.0
    return 1.0


def _score_symbols(text: str, as_of_date: date, symbol_map: dict[str, Any]) -> tuple[float, list[str], dict[str, int]]:
    lowered = text.lower()
    score = 0.0
    matched_symbols: list[str] = []
    bias_counts = {"up": 0, "down": 0}
    symbols = symbol_map.get("symbols")
    lane_weights_obj = symbol_map.get("corpus_lane_weights")
    lane_weights: dict[str, float] = {}
    if isinstance(lane_weights_obj, dict):
        for k, v in lane_weights_obj.items():
            try:
                lane_weights[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
    if not isinstance(symbols, list):
        return score, matched_symbols, bias_counts
    regime_mul = _regime_multiplier(as_of_date, symbol_map)
    for item in symbols:
        if not isinstance(item, dict):
            continue
        symbol_id = str(item.get("symbol_id") or "").strip()
        direction = _normalize_label_direction(str(item.get("direction_bias") or "neutral"))
        weight = float(item.get("weight") or 0.0)
        lane = str(item.get("corpus_lane") or "canon").strip().lower()
        lane_weight = lane_weights.get(lane, 1.0)
        keywords = item.get("keywords")
        if not symbol_id or not isinstance(keywords, list):
            continue
        hit = any(str(k).lower() in lowered for k in keywords if str(k).strip())
        if not hit:
            continue
        matched_symbols.append(symbol_id)
        effective_weight = weight * lane_weight
        if direction == "up":
            score += effective_weight
            bias_counts["up"] += 1
        elif direction == "down":
            score -= effective_weight
            bias_counts["down"] += 1

    score *= regime_mul

    symbolic_inference = symbol_map.get("symbolic_inference")
    if isinstance(symbolic_inference, dict):
        # If both bullish and bearish symbols fire simultaneously, dampen overconfident calls.
        if bias_counts["up"] > 0 and bias_counts["down"] > 0:
            try:
                conflict_damp = float(symbolic_inference.get("conflict_dampen") or 1.0)
            except (TypeError, ValueError):
                conflict_damp = 1.0
            score *= max(0.0, min(conflict_damp, 1.0))

    return score, matched_symbols, bias_counts


def _direction_from_score(score: float, neutral_band: float) -> str:
    if score > neutral_band:
        return "up"
    if score < -neutral_band:
        return "down"
    return "neutral"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Logos symbolic event backtest (B-track only).")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--labels-jsonl", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--symbol-map-json", type=Path, default=DEFAULT_SYMBOL_MAP)
    ap.add_argument("--instrument-id", type=str, default="KOSPI")
    ap.add_argument("--horizon", type=str, default="1d")
    ap.add_argument("--neutral-score-band", type=float, default=0.25)
    ap.add_argument(
        "--synthetic-source-ids",
        type=str,
        default="label_guided_seed,manual_seed",
        help="Comma-separated source_id values treated as synthetic/seed.",
    )
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT_CSV)
    args = ap.parse_args()

    if not args.news_jsonl.is_file():
        raise SystemExit(f"Missing --news-jsonl: {args.news_jsonl}")
    if not args.labels_jsonl.is_file():
        raise SystemExit(f"Missing --labels-jsonl: {args.labels_jsonl}")
    if not args.symbol_map_json.is_file():
        raise SystemExit(f"Missing --symbol-map-json: {args.symbol_map_json}")

    instrument_id = str(args.instrument_id).strip()
    horizon = str(args.horizon).strip().lower()
    symbol_map = _load_json(args.symbol_map_json)
    news_rows = [r for r in _load_jsonl(args.news_jsonl) if r.get("schema_version") == "news_observation_v1"]
    label_rows = [r for r in _load_jsonl(args.labels_jsonl) if r.get("schema_version") == "direction_label_bar_v1"]

    filtered_labels = [
        r
        for r in label_rows
        if str(r.get("instrument_id") or "").strip() == instrument_id
        and str(r.get("horizon") or "").strip().lower() == horizon
    ]
    filtered_labels.sort(key=lambda r: _parse_label_date(str(r.get("label_date") or "1970-01-01")))

    rows: list[dict[str, Any]] = []
    symbol_hits: dict[str, int] = {}
    warnings: list[str] = []
    split_stats: dict[str, dict[str, int]] = {}
    non_synthetic_n = 0
    non_synthetic_hits = 0
    synthetic_source_ids = {x.strip() for x in str(args.synthetic_source_ids).split(",") if x.strip()}

    for row in news_rows:
        try:
            as_of_date = _parse_as_of_date_utc(str(row.get("as_of_utc") or ""))
        except Exception:
            warnings.append(f"bad_as_of_utc:{row.get('observation_id')}")
            continue
        label = next(
            (lb for lb in filtered_labels if _parse_label_date(str(lb.get("label_date") or "")) > as_of_date),
            None,
        )
        if label is None:
            warnings.append(f"missing_future_label:{row.get('observation_id')}")
            continue
        canonical_text = str(row.get("canonical_text") or "")
        score, matched_symbols, bias_counts = _score_symbols(canonical_text, as_of_date, symbol_map)
        predicted = _direction_from_score(score, float(args.neutral_score_band))
        actual = _normalize_label_direction(str(label.get("direction") or "neutral"))
        hit = int(predicted == actual)
        split = str(row.get("dataset_partition") or "unspecified")
        source_id = str(row.get("source_id") or "")
        is_synthetic_source = source_id in synthetic_source_ids

        for sid in matched_symbols:
            symbol_hits[sid] = symbol_hits.get(sid, 0) + 1

        rows.append(
            {
                "observation_id": str(row.get("observation_id") or ""),
                "as_of_utc": str(row.get("as_of_utc") or ""),
                "label_date": str(label.get("label_date") or ""),
                "dataset_partition": split,
                "source_id": source_id,
                "is_synthetic_source": is_synthetic_source,
                "instrument_id": instrument_id,
                "horizon": horizon,
                "score": round(score, 6),
                "predicted_direction": predicted,
                "actual_direction": actual,
                "hit": hit,
                "bias_up_hits": bias_counts["up"],
                "bias_down_hits": bias_counts["down"],
                "matched_symbols": matched_symbols,
            }
        )
        split_bucket = split_stats.setdefault(split, {"n": 0, "hits": 0})
        split_bucket["n"] += 1
        split_bucket["hits"] += hit
        if not is_synthetic_source:
            non_synthetic_n += 1
            non_synthetic_hits += hit

    n = len(rows)
    hits = sum(int(r["hit"]) for r in rows)
    coverage = len(symbol_hits)
    summary = {
        "n_evaluated": n,
        "hits": hits,
        "hit_rate": round(hits / n, 6) if n else None,
        "symbol_coverage_count": coverage,
        "neutral_score_band": float(args.neutral_score_band),
        "non_synthetic_n_evaluated": non_synthetic_n,
        "non_synthetic_hit_rate": round(non_synthetic_hits / non_synthetic_n, 6) if non_synthetic_n else None,
    }
    split_summary = {
        k: {
            "n_evaluated": v["n"],
            "hits": v["hits"],
            "hit_rate": round(v["hits"] / v["n"], 6) if v["n"] else None,
        }
        for k, v in split_stats.items()
    }

    payload = {
        "schema": "logos_symbolic_event_backtest_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "news_jsonl": str(args.news_jsonl).replace("\\", "/"),
            "labels_jsonl": str(args.labels_jsonl).replace("\\", "/"),
            "symbol_map_json": str(args.symbol_map_json).replace("\\", "/"),
            "instrument_id": instrument_id,
            "horizon": horizon,
            "synthetic_source_ids": sorted(list(synthetic_source_ids)),
        },
        "summary": summary,
        "split_summary": split_summary,
        "symbol_hit_counts": symbol_hits,
        "rows": rows,
        "warnings": warnings,
        "notes": [
            "[B-TRACK][HYPO] Symbolic mapping is observational and not a direct live-trading trigger."
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "observation_id",
                "as_of_utc",
                "label_date",
                "dataset_partition",
                "source_id",
                "is_synthetic_source",
                "instrument_id",
                "horizon",
                "score",
                "predicted_direction",
                "actual_direction",
                "hit",
                "bias_up_hits",
                "bias_down_hits",
                "matched_symbols",
            ],
        )
        writer.writeheader()
        for r in rows:
            dumped = dict(r)
            dumped["matched_symbols"] = ",".join(r.get("matched_symbols") or [])
            writer.writerow(dumped)

    print(json.dumps({"ok": True, "n_evaluated": n, "hit_rate": summary["hit_rate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

