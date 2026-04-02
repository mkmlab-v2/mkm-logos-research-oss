# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.6, M:0.6}
# Balance: 88
# Purpose: Build leakage-resistant blind historical replay datasets.
# Keywords: blind-replay, masking, leakage, exploratory_only, backtest
#!/usr/bin/env python3
"""Build blind historical replay artifacts from OHLCV CSV.

This script is intentionally isolated from A-track execution paths.
It produces:
1) public masked prompts (no date/asset/absolute price)
2) private answer key for offline scoring only

Use this as B-track exploratory evidence only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "blind_replay"


@dataclass
class Row:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(v: Any) -> float:
    return float(str(v).strip())


def _safe_ratio(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


def _zscore(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return [0.0 for _ in values]
    return [(x - mean) / std for x in values]


def _load_csv(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"open", "high", "low", "close", "volume"}
        lower_headers = {h.lower(): h for h in (reader.fieldnames or [])}
        if not required.issubset(set(lower_headers.keys())):
            raise ValueError("CSV requires columns: open, high, low, close, volume (+ optional timestamp/date)")
        ts_key = lower_headers.get("timestamp") or lower_headers.get("date") or lower_headers.get("time")
        for i, r in enumerate(reader):
            ts = str(r.get(ts_key) if ts_key else f"row_{i:06d}")
            rows.append(
                Row(
                    ts=ts,
                    open=_to_float(r[lower_headers["open"]]),
                    high=_to_float(r[lower_headers["high"]]),
                    low=_to_float(r[lower_headers["low"]]),
                    close=_to_float(r[lower_headers["close"]]),
                    volume=_to_float(r[lower_headers["volume"]]),
                )
            )
    if len(rows) < 40:
        raise ValueError("Need at least 40 rows for blind replay windows.")
    return rows


def _build_features(window: list[Row]) -> dict[str, float]:
    closes = [r.close for r in window]
    vols = [r.volume for r in window]
    rets = [0.0]
    for i in range(1, len(closes)):
        rets.append(_safe_ratio(closes[i] - closes[i - 1], closes[i - 1]))
    abs_rets = [abs(x) for x in rets[1:]]
    vol_idx = sum(abs_rets) / len(abs_rets) if abs_rets else 0.0
    momentum = _safe_ratio(closes[-1] - closes[0], closes[0])
    range_spread = _safe_ratio(max(closes) - min(closes), max(min(closes), 1e-9))
    volume_z_last = _zscore(vols)[-1] if vols else 0.0
    drawdown = _safe_ratio(closes[-1] - max(closes), max(closes) if closes else 1.0)
    # Phase C.1 features: regime shift and candle-shape pressure
    short = abs_rets[-5:] if len(abs_rets) >= 5 else abs_rets
    long = abs_rets[-20:] if len(abs_rets) >= 20 else abs_rets
    short_vol = (sum(short) / len(short)) if short else 0.0
    long_vol = (sum(long) / len(long)) if long else 0.0
    vol_regime_shift = _safe_ratio(short_vol - long_vol, max(long_vol, 1e-9))
    last_n = rets[-10:] if len(rets) >= 10 else rets
    non_zero = [x for x in last_n if abs(x) > 1e-12]
    pos = len([x for x in non_zero if x > 0])
    neg = len([x for x in non_zero if x < 0])
    trend_consistency = _safe_ratio(abs(pos - neg), len(non_zero)) if non_zero else 0.0
    wick_bias_vals: list[float] = []
    for r in window[-10:] if len(window) >= 10 else window:
        candle_range = max(r.high - r.low, 1e-9)
        upper_wick = max(0.0, r.high - max(r.open, r.close))
        lower_wick = max(0.0, min(r.open, r.close) - r.low)
        wick_bias_vals.append(_safe_ratio(upper_wick - lower_wick, candle_range))
    wick_bias = (sum(wick_bias_vals) / len(wick_bias_vals)) if wick_bias_vals else 0.0
    return {
        "volatility_index": round(vol_idx, 6),
        "momentum_index": round(momentum, 6),
        "range_spread_index": round(range_spread, 6),
        "volume_pressure_z": round(volume_z_last, 6),
        "drawdown_index": round(drawdown, 6),
        "vol_regime_shift": round(vol_regime_shift, 6),
        "trend_consistency": round(trend_consistency, 6),
        "wick_bias_index": round(wick_bias, 6),
    }


def _label_next_horizon(next_rows: list[Row], down_th: float, up_th: float) -> tuple[str, float]:
    if not next_rows:
        return "UNKNOWN", 0.0
    start = next_rows[0].open
    end = next_rows[-1].close
    ret = _safe_ratio(end - start, start)
    if ret <= down_th:
        return "DOWN_STRONG", ret
    if ret >= up_th:
        return "UP_STRONG", ret
    return "NEUTRAL", ret


def _prompt_text(features: dict[str, float], horizon: int) -> str:
    return (
        "Asset_Alpha has the following masked state-energy profile. "
        "Do not infer real-world event names or dates. "
        f"Target horizon is next {horizon} bars.\n"
        f"- VolatilityIndex: {features['volatility_index']}\n"
        f"- MomentumIndex: {features['momentum_index']}\n"
        f"- RangeSpreadIndex: {features['range_spread_index']}\n"
        f"- VolumePressureZ: {features['volume_pressure_z']}\n"
        f"- DrawdownIndex: {features['drawdown_index']}\n"
        f"- VolRegimeShift: {features['vol_regime_shift']}\n"
        f"- TrendConsistency: {features['trend_consistency']}\n"
        f"- WickBiasIndex: {features['wick_bias_index']}\n"
        "Return only JSON with keys: direction_sign, confidence_0_1, rationale_short."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate blind historical replay artifacts (exploratory only).")
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--window-bars", type=int, default=30)
    ap.add_argument("--horizon-bars", type=int, default=5)
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--sample-size", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--down-threshold", type=float, default=-0.008)
    ap.add_argument("--up-threshold", type=float, default=0.015)
    args = ap.parse_args()

    rows = _load_csv(args.input_csv)
    total_needed = args.window_bars + args.horizon_bars
    max_start = len(rows) - total_needed
    if max_start <= 0:
        raise SystemExit("Not enough rows for configured window+horizon.")

    starts = list(range(0, max_start + 1, max(1, args.stride)))
    random.Random(args.seed).shuffle(starts)
    starts = starts[: max(1, args.sample_size)]

    public_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for idx, s in enumerate(starts, start=1):
        w = rows[s : s + args.window_bars]
        h = rows[s + args.window_bars : s + total_needed]
        features = _build_features(w)
        label, realized_ret = _label_next_horizon(h, args.down_threshold, args.up_threshold)
        sample_id = f"BR_{idx:05d}"
        digest = hashlib.sha256(
            f"{w[0].ts}|{w[-1].ts}|{h[-1].ts}|{args.seed}".encode("utf-8")
        ).hexdigest()[:16]

        public_rows.append(
            {
                "sample_id": sample_id,
                "blind_bucket_id": f"Bucket_{digest}",
                "exploratory_only": True,
                "prompt": _prompt_text(features, args.horizon_bars),
                "features": features,
            }
        )
        key_rows.append(
            {
                "sample_id": sample_id,
                "blind_bucket_id": f"Bucket_{digest}",
                "answer_label": label,
                "realized_return_pct": round(realized_ret * 100.0, 6),
                "ts_window_start": w[0].ts,
                "ts_window_end": w[-1].ts,
                "ts_horizon_end": h[-1].ts if h else None,
            }
        )

    run_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    public_path = out_dir / f"blind_replay_public_{run_tag}.jsonl"
    key_path = out_dir / f"blind_replay_answer_key_{run_tag}.jsonl"
    manifest_path = out_dir / "blind_replay_manifest_latest.json"

    with public_path.open("w", encoding="utf-8") as f:
        for r in public_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with key_path.open("w", encoding="utf-8") as f:
        for r in key_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "schema": "blind_historical_replay_manifest_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "input_csv": str(args.input_csv.resolve()),
        "public_dataset": str(public_path.resolve()),
        "private_answer_key": str(key_path.resolve()),
        "sample_count": len(public_rows),
        "window_bars": args.window_bars,
        "horizon_bars": args.horizon_bars,
        "stride": args.stride,
        "leakage_controls": {
            "date_masking": True,
            "asset_name_masking": True,
            "absolute_price_removed": True,
            "evaluation_separated_by_private_key": True,
        },
        "note": "B-track isolated experiment only; do not connect to live trigger path.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {public_path}")
    print(f"WROTE: {key_path}")
    print(f"WROTE: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
