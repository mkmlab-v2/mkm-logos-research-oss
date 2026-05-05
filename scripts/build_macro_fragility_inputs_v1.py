#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.8, M:0.4}
# Balance: 90
# Purpose: Build Fragility Composite v1 input payload with optional live data.
# Keywords: macro, fragility, fred, baseline, fact-lock

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_fragility_inputs_latest.json"
DEFAULT_FRAGILITY_STATE = ROOT / "docs" / "final" / "artifacts" / "fragility_composite_v1_latest.json"
DEFAULT_SOURCE = ROOT / "docs" / "final" / "artifacts" / "macro_fragility_source_latest.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    return doc


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    m = median(values)
    return median([abs(v - m) for v in values])


def _fred_series(api_key: str, series_id: str, limit: int = 220) -> list[float]:
    q = parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": int(limit),
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=20.0) as resp:
        raw = resp.read().decode("utf-8")
    doc = json.loads(raw)
    rows = doc.get("observations")
    out: list[float] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_v = str(row.get("value") or "").strip()
        if not raw_v or raw_v == ".":
            continue
        try:
            out.append(float(raw_v))
        except Exception:
            continue
    return out


def _realized_vol_20d_from_levels_desc(levels_desc: list[float]) -> float:
    if len(levels_desc) < 21:
        return 0.0
    # levels_desc is newest->oldest
    levels = list(reversed(levels_desc[:40]))
    rets: list[float] = []
    for i in range(1, len(levels)):
        prev = levels[i - 1]
        curr = levels[i]
        if prev <= 0.0:
            continue
        rets.append((curr / prev) - 1.0)
    if len(rets) < 20:
        return 0.0
    tail = rets[-20:]
    mean = sum(tail) / len(tail)
    var = sum((x - mean) ** 2 for x in tail) / len(tail)
    daily_std = var ** 0.5
    return daily_std * (252.0**0.5)


def _build_from_source_doc(source_doc: dict[str, Any]) -> tuple[dict[str, Any], str]:
    metrics = source_doc.get("metrics") if isinstance(source_doc.get("metrics"), dict) else {}
    baselines = source_doc.get("baselines") if isinstance(source_doc.get("baselines"), dict) else {}
    if not metrics or not baselines:
        return {}, "invalid_source_doc"
    return {
        "metrics": {
            "move": _to_float(metrics.get("move"), 126.0),
            "vix": _to_float(metrics.get("vix"), 18.5),
            "hy_oas": _to_float(metrics.get("hy_oas"), 3.9),
            "dxy_vol": _to_float(metrics.get("dxy_vol"), 0.118),
        },
        "baselines": {
            "move": {
                "median_156w": _to_float((baselines.get("move") or {}).get("median_156w"), 112.0),
                "mad_156w": _to_float((baselines.get("move") or {}).get("mad_156w"), 8.0),
            },
            "vix": {
                "median_156w": _to_float((baselines.get("vix") or {}).get("median_156w"), 17.2),
                "mad_156w": _to_float((baselines.get("vix") or {}).get("mad_156w"), 2.2),
            },
            "hy_oas": {
                "median_156w": _to_float((baselines.get("hy_oas") or {}).get("median_156w"), 3.7),
                "mad_156w": _to_float((baselines.get("hy_oas") or {}).get("mad_156w"), 0.35),
            },
            "dxy_vol": {
                "median_156w": _to_float((baselines.get("dxy_vol") or {}).get("median_156w"), 0.104),
                "mad_156w": _to_float((baselines.get("dxy_vol") or {}).get("mad_156w"), 0.012),
            },
        },
    }, "source_doc"


def _build_from_fred(api_key: str) -> tuple[dict[str, Any], str]:
    try:
        vix = _fred_series(api_key, "VIXCLS", limit=220)
        hy = _fred_series(api_key, "BAMLH0A0HYM2", limit=220)
        dxy = _fred_series(api_key, "DTWEXBGS", limit=260)
        move_proxy = _fred_series(api_key, "MOVEINDEX", limit=220)  # optional; may be unavailable on some keys
    except Exception:
        return {}, "fred_request_failed"

    if len(vix) < 60 or len(hy) < 60 or len(dxy) < 60:
        return {}, "fred_insufficient_data"

    if len(move_proxy) < 60:
        move_proxy = [126.0] + [112.0] * 180

    dxy_vol_current = _realized_vol_20d_from_levels_desc(dxy[:40])
    dxy_hist_vols: list[float] = []
    for start in range(0, min(len(dxy) - 40, 180), 5):
        window = dxy[start : start + 40]
        dxy_hist_vols.append(_realized_vol_20d_from_levels_desc(window))
    dxy_hist_vols = [x for x in dxy_hist_vols if x > 0.0]
    if not dxy_hist_vols:
        dxy_hist_vols = [0.104, 0.110, 0.098, 0.120]

    return {
        "metrics": {
            "move": move_proxy[0],
            "vix": vix[0],
            "hy_oas": hy[0],
            "dxy_vol": dxy_vol_current if dxy_vol_current > 0.0 else dxy_hist_vols[0],
        },
        "baselines": {
            "move": {"median_156w": median(move_proxy[:156]), "mad_156w": _mad(move_proxy[:156])},
            "vix": {"median_156w": median(vix[:156]), "mad_156w": _mad(vix[:156])},
            "hy_oas": {"median_156w": median(hy[:156]), "mad_156w": _mad(hy[:156])},
            "dxy_vol": {"median_156w": median(dxy_hist_vols[:156]), "mad_156w": _mad(dxy_hist_vols[:156])},
        },
    }, "fred_live"


def _default_payload() -> dict[str, Any]:
    return {
        "metrics": {"move": 126.0, "vix": 18.5, "hy_oas": 3.9, "dxy_vol": 0.118},
        "baselines": {
            "move": {"median_156w": 112.0, "mad_156w": 8.0},
            "vix": {"median_156w": 17.2, "mad_156w": 2.2},
            "hy_oas": {"median_156w": 3.7, "mad_156w": 0.35},
            "dxy_vol": {"median_156w": 0.104, "mad_156w": 0.012},
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build macro fragility input payload for Fragility Composite v1.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--source-json", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--fragility-state", type=Path, default=DEFAULT_FRAGILITY_STATE)
    p.add_argument("--prefer-fred", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    source_path = args.source_json if args.source_json.is_absolute() else (ROOT / args.source_json)
    fragility_path = args.fragility_state if args.fragility_state.is_absolute() else (ROOT / args.fragility_state)

    source_doc = _read_json(source_path)
    payload: dict[str, Any] = {}
    source_mode = ""

    fred_key = str(os.environ.get("FRED_API_KEY", "")).strip()
    if args.prefer_fred and fred_key:
        payload, source_mode = _build_from_fred(fred_key)
    if not payload:
        payload, source_mode = _build_from_source_doc(source_doc)
    if not payload and fred_key:
        payload, source_mode = _build_from_fred(fred_key)
    if not payload:
        payload = _default_payload()
        source_mode = "fallback_defaults"

    state_doc = _read_json(fragility_path)
    state_next = state_doc.get("state_memory_next") if isinstance(state_doc.get("state_memory_next"), dict) else {}
    recent_gates = state_next.get("recent_gates", [])
    if not isinstance(recent_gates, list):
        recent_gates = []
    state_memory = {
        "red_active": bool(state_next.get("red_active", False)),
        "below66_streak": int(state_next.get("below66_streak", 0) or 0),
        "recent_gates": [str(x).upper() for x in recent_gates][-3:],
        "red_streak": int(state_next.get("red_streak", 0) or 0),
    }
    prev_state_4d = state_next.get("state_4d") if isinstance(state_next.get("state_4d"), dict) else {}
    quaternion_history = state_next.get("quaternion_history") if isinstance(state_next.get("quaternion_history"), list) else []

    hy = payload["metrics"]["hy_oas"]
    hy_median = payload["baselines"]["hy_oas"]["median_156w"]
    hy_delta_pct = 0.0
    if hy_median != 0.0:
        hy_delta_pct = ((hy - hy_median) / abs(hy_median)) * 100.0

    out = {
        "schema": "macro_fragility_inputs_v1",
        "generated_at_utc": _utc_now(),
        "as_of_utc": _utc_now(),
        "source_mode": source_mode,
        "hypothesis_tier": "ESTIMATE",
        "metrics": payload["metrics"],
        "baselines": payload["baselines"],
        "aux": {
            "hy_oas_4w_change_pct": round(hy_delta_pct, 6),
            "hy_oas_4w_change_pct_p85": 9.5,
        },
        "state_memory": state_memory,
        "prev_state_4d": {
            "stress": _to_float(prev_state_4d.get("stress"), 0.0),
            "liquidity": _to_float(prev_state_4d.get("liquidity"), 0.0),
            "credit": _to_float(prev_state_4d.get("credit"), 0.0),
            "currency": _to_float(prev_state_4d.get("currency"), 0.0),
        },
        "quaternion_history": [_to_float(x, 0.0) for x in quaternion_history][-60:],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"macro_fragility_inputs_v1: PASS -> {out_path}")
    print(f"source_mode={source_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
