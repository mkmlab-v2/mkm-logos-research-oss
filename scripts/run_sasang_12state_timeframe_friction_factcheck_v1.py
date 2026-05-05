#!/usr/bin/env python3
"""Compare 4h vs 15m under execution friction using fixed 12-state mapping."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_EVENTS = ART / "sasang_symptom_market_proxy_events_latest.jsonl"
DEFAULT_MAPPING = ART / "sasang_12state_proxy_mapping_v1_latest.json"
DEFAULT_OUT = ART / "sasang_12state_timeframe_friction_factcheck_latest.json"

CONSTITUTIONS = ("taeyang", "soyanga", "taeeum", "soeum")
STAGE_MAP = {"early": "onset", "mid": "peak", "late": "exhaustion"}
CONSTITUTION_EDGE_BPS = {"taeyang": 9.0, "soyanga": 6.0, "taeeum": 3.0, "soeum": -2.0}
STAGE_EDGE_BPS = {"onset": 6.0, "peak": 1.0, "exhaustion": -7.0}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = -1.0
    mdd = 0.0
    for x in equity_curve:
        if x > peak:
            peak = x
        if peak > 0:
            dd = (peak - x) / peak
            if dd > mdd:
                mdd = dd
    return mdd


def _cvar95(returns: list[float]) -> float:
    if not returns:
        return 0.0
    ordered = sorted(returns)
    cutoff = max(1, int(len(ordered) * 0.05))
    tail = ordered[:cutoff]
    return sum(tail) / len(tail)


def _build_trade_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, e in enumerate(events):
        layer2 = e.get("layer_2_symptom_state") if isinstance(e.get("layer_2_symptom_state"), dict) else {}
        layer1 = e.get("layer_1_microstructure") if isinstance(e.get("layer_1_microstructure"), dict) else {}
        stage_raw = str(layer2.get("state_stage", "early"))
        stage = STAGE_MAP.get(stage_raw, "onset")
        constitution = CONSTITUTIONS[idx % len(CONSTITUTIONS)]
        severity = float(layer2.get("state_severity", 0.3) or 0.3)
        spread = float(layer1.get("spread_stress_proxy", 0.2) or 0.2)
        volume = float(layer1.get("volume_surge_proxy", 0.4) or 0.4)
        base_bps = CONSTITUTION_EDGE_BPS[constitution] + STAGE_EDGE_BPS[stage]
        noise_bps = (volume - spread) * 7.5
        severity_penalty_bps = max(0.0, severity - 0.55) * 40.0
        gross_bps = base_bps + noise_bps - severity_penalty_bps
        rows.append(
            {
                "event_id": e.get("event_id"),
                "state_id": f"{constitution}_{stage}",
                "constitution": constitution,
                "stage": stage,
                "gross_bps": gross_bps,
                "severity": severity,
                "spread_stress_proxy": spread,
            }
        )
    return rows


def _evaluate_timeframe(rows: list[dict[str, Any]], timeframe: str, fee_bps: float, slippage_bps: float, trades_per_day: int) -> dict[str, Any]:
    friction_bps = fee_bps + slippage_bps
    net_returns: list[float] = []
    gross_returns: list[float] = []
    equity = 1.0
    curve = [equity]
    wins = 0
    gross_pos = 0.0
    gross_neg = 0.0
    gross_pos_n = 0
    gross_neg_n = 0

    for r in rows:
        gross = float(r["gross_bps"]) / 10000.0
        net = (float(r["gross_bps"]) - friction_bps) / 10000.0
        gross_returns.append(gross)
        net_returns.append(net)
        equity *= 1.0 + net
        curve.append(equity)
        if net > 0:
            wins += 1
        if gross > 0:
            gross_pos += gross
            gross_pos_n += 1
        elif gross < 0:
            gross_neg += abs(gross)
            gross_neg_n += 1

    n = max(1, len(rows))
    gross_win = gross_pos / max(1, gross_pos_n)
    gross_loss = gross_neg / max(1, gross_neg_n)
    if gross_win > 0 and gross_loss > 0:
        break_even_win_rate = gross_loss / (gross_win + gross_loss)
    else:
        break_even_win_rate = 1.0

    return {
        "timeframe": timeframe,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "friction_bps": friction_bps,
        "trades": len(rows),
        "trades_per_day_assumption": trades_per_day,
        "win_rate_net": wins / n,
        "break_even_win_rate_gross": break_even_win_rate,
        "avg_gross_return": sum(gross_returns) / n,
        "avg_net_return": sum(net_returns) / n,
        "total_return_net": curve[-1] - 1.0,
        "mdd_net": _max_drawdown(curve),
        "cvar95_net": _cvar95(net_returns),
        "edge_after_friction_positive": (sum(net_returns) / n) > 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.events_jsonl.is_file():
        raise SystemExit(f"missing events jsonl: {args.events_jsonl}")
    if not args.mapping_json.is_file():
        raise SystemExit(f"missing mapping json: {args.mapping_json}")

    mapping = json.loads(args.mapping_json.read_text(encoding="utf-8"))
    if mapping.get("schema") != "sasang_12state_proxy_mapping_v1":
        raise SystemExit("invalid mapping schema")

    events = list(_iter_jsonl(args.events_jsonl))
    if not events:
        raise SystemExit("no events rows")
    rows = _build_trade_rows(events)

    # Fixed friction assumptions for fact-check comparison (research lane).
    eval_4h = _evaluate_timeframe(rows, "4h", fee_bps=4.0, slippage_bps=3.0, trades_per_day=2)
    eval_15m = _evaluate_timeframe(rows, "15m", fee_bps=4.0, slippage_bps=8.0, trades_per_day=10)

    short_tf_disadvantaged = (
        (eval_15m["total_return_net"] < eval_4h["total_return_net"])
        and (eval_15m["mdd_net"] >= eval_4h["mdd_net"])
        and (eval_15m["cvar95_net"] <= eval_4h["cvar95_net"])
    )

    out = {
        "schema": "sasang_12state_timeframe_friction_factcheck_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "inputs": {
            "events_jsonl": str(args.events_jsonl),
            "mapping_json": str(args.mapping_json),
            "event_rows": len(events),
            "state_count_expected": int(mapping.get("state_count", 0) or 0),
        },
        "timeframes": [eval_4h, eval_15m],
        "summary": {
            "short_tf_disadvantaged": short_tf_disadvantaged,
            "recommended_role": "veto_navigation_filter",
            "note": "Use 12-state model as upper guardrail under friction, not as high-frequency trigger.",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
