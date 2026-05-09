#!/usr/bin/env python3
"""Minimal 4h B-track prophecy artifact refresher for VPS bootstrap.

Writes:
- docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
- docs/final/artifacts/btrack_prophecy_score_latest.json
- docs/final/artifacts/prophecy_hit_rate_eval_latest.json

This is a bootstrap chain for environments where full B-track scripts are
not yet deployed. It uses:
- local trading_state observation
- Binance public 4h kline (closed bar) for realized direction
- lightweight confidence auto-adjust (mini auto-evolution)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path("/opt/bitcoin-trading")
ART = ROOT / "docs" / "final" / "artifacts"
STATE = ROOT / "logs" / "trading_state.json"
AUTOEVO = ART / "btrack_4h_autoevo_latest.json"
BFX_4H_URL = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=4h&limit=3"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _direction_from_state(state: dict[str, Any]) -> str:
    sig = str(state.get("last_signal") or "").strip().upper()
    if sig in {"LONG", "BUY"}:
        return "bull"
    if sig in {"SHORT", "SELL"}:
        return "bear"
    return "neutral"


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fetch_last_closed_4h_direction() -> tuple[str, dict[str, Any]]:
    """Return (direction, meta) using last two closed 4h bars."""
    try:
        with urlopen(BFX_4H_URL, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
        arr = json.loads(raw)
        if not isinstance(arr, list) or len(arr) < 2:
            return "neutral", {"status": "no_data"}
        prev_bar = arr[-2]
        close_prev = float(prev_bar[4])
        open_prev = float(prev_bar[1])
        if close_prev > open_prev:
            d = "bull"
        elif close_prev < open_prev:
            d = "bear"
        else:
            d = "neutral"
        return d, {
            "status": "ok",
            "kline_open_time_ms": prev_bar[0],
            "open": open_prev,
            "close": close_prev,
        }
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        return "neutral", {"status": "error", "error": str(e)}


def _autoevo_confidence(
    base_conf: float, predicted: str, realized: str, prev_evo: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    total = int(prev_evo.get("n_evaluated", 0) or 0)
    hits = int(prev_evo.get("hits", 0) or 0)
    if predicted in {"bull", "bear", "neutral"} and realized in {"bull", "bear", "neutral"}:
        total += 1
        if predicted == realized:
            hits += 1
    hit_rate = (hits / total) if total > 0 else 0.5
    # Mini adaptive rule: scale confidence by realized rolling quality.
    if hit_rate >= 0.60:
        conf = min(0.70, base_conf + 0.05)
    elif hit_rate <= 0.40:
        conf = max(0.45, base_conf - 0.05)
    else:
        conf = base_conf
    return conf, {"n_evaluated": total, "hits": hits, "rolling_hit_rate": round(hit_rate, 4)}


def main() -> int:
    now = _utc_now()
    state = _read_json(STATE)
    predicted_direction = _direction_from_state(state)
    base_conf = 0.55 if predicted_direction in {"bull", "bear"} else 0.5
    realized_direction, realized_meta = _fetch_last_closed_4h_direction()
    prev_evo = _read_json(AUTOEVO)
    confidence, evo = _autoevo_confidence(base_conf, predicted_direction, realized_direction, prev_evo)

    hypothesis = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "version": "bootstrap_minimal_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": "[HYPO] bootstrap minimal 4h prophecy from local trading_state + Binance 4h realized feedback; research_only",
        "prediction": {
            "instrument": "btc",
            "horizon": "4h",
            "direction": predicted_direction,
            "confidence": confidence,
        },
        "runtime_meta": {
            "source": str(STATE),
            "state_schema": state.get("schema"),
            "engine": state.get("engine"),
            "last_signal": state.get("last_signal"),
            "realized_4h_direction": realized_direction,
            "realized_4h_meta": realized_meta,
            "autoevo": evo,
        },
    }

    score = {
        "schema": "btrack_prophecy_score_v1",
        "generated_at_utc": now,
        "eval_date": now[:10],
        "rows": [
            {
                "instrument": "btc",
                "eval_date": now[:10],
                "predicted_direction": predicted_direction,
                "actual_direction": realized_direction,
                "daily_return": 0.0,
                "note": "bootstrap row from Binance last closed 4h bar direction (full OHLCV chain not deployed on VPS)",
            }
        ],
        "meta": {"bootstrap_mode": True, "realized_4h_meta": realized_meta},
    }

    hit_rate = evo["rolling_hit_rate"]
    hit_rate = {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "generated_at_utc": now,
        "run_mode": "price",
        "status": "ok",
        "zeroing_note": "bootstrap mini auto-evolution eval; replace with full B-track scoring chain when deployed",
        "metrics": {
            "price_directional_hit_rate": hit_rate,
            "n_evaluated": evo["n_evaluated"],
            "price_hits": evo["hits"],
        },
    }

    _write(ART / "btrack_hypothesis_prophecy_latest.json", hypothesis)
    _write(ART / "btrack_prophecy_score_latest.json", score)
    _write(ART / "prophecy_hit_rate_eval_latest.json", hit_rate)
    _write(AUTOEVO, {"schema": "btrack_4h_autoevo_v1", "updated_at_utc": now, **evo})
    print("WROTE bootstrap 4h prophecy artifacts + mini autoevo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
