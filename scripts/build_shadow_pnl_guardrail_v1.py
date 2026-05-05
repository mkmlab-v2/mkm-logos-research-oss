#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_price_from_obj(obj: Any) -> float | None:
    if isinstance(obj, dict):
        for key in (
            "btc_price_usd",
            "price_usd",
            "price",
            "lastPrice",
            "markPrice",
            "close",
            "value",
        ):
            v = obj.get(key)
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v)
                except ValueError:
                    pass
        for v in obj.values():
            p = _extract_price_from_obj(v)
            if p is not None:
                return p
    elif isinstance(obj, list):
        for item in obj:
            p = _extract_price_from_obj(item)
            if p is not None:
                return p
    return None


def _fetch_binance_price(timeout_sec: float) -> float | None:
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            price = payload.get("price")
            return float(price) if price is not None else None
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build shadow PnL guardrail report for HOLD/WATCH states.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument(
        "--readiness-json",
        default="docs/final/artifacts/operational_readiness_checklist_v1_latest.json",
    )
    ap.add_argument(
        "--briefing-json",
        default="docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json",
    )
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/shadow_pnl_guardrail_latest.json",
    )
    ap.add_argument("--notional-usd", type=float, default=1000.0)
    ap.add_argument("--price-usd", type=float, default=0.0)
    ap.add_argument("--price-source-json", default="")
    ap.add_argument("--network-timeout-sec", type=float, default=3.0)
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    readiness = _read_json(root / args.readiness_json)
    briefing = _read_json(root / args.briefing_json)
    out_path = root / args.out
    prev = _read_json(out_path)

    judge_decision = str((readiness.get("verification") or {}).get("judge_decision", "UNKNOWN"))
    decision_state = str((briefing.get("market_snapshot") or {}).get("decision_state", "UNKNOWN"))
    operator_action = str((briefing.get("action_frame") or {}).get("operator_action", ""))
    guard_active = judge_decision in {"HOLD"} or decision_state in {"WATCH", "HOLD"}

    price_usd: float | None = None
    price_source = "none"
    if args.price_usd > 0:
        price_usd = float(args.price_usd)
        price_source = "cli"
    elif args.price_source_json:
        src_obj = _read_json(root / args.price_source_json)
        price_usd = _extract_price_from_obj(src_obj)
        if price_usd is not None:
            price_source = f"json:{args.price_source_json}"
    if price_usd is None:
        price_usd = _fetch_binance_price(args.network_timeout_sec)
        if price_usd is not None:
            price_source = "binance_public_api"

    prev_price = prev.get("price_context", {}).get("current_price_usd")
    prev_price = float(prev_price) if isinstance(prev_price, (int, float)) else None
    delta_pct = None
    delta_usd = None
    avoided_loss_usd = float((prev.get("impact") or {}).get("cumulative_avoided_loss_usd", 0.0))
    missed_opportunity_usd = float((prev.get("impact") or {}).get("cumulative_missed_opportunity_usd", 0.0))
    latest_cycle_impact = {"avoided_loss_usd": 0.0, "missed_opportunity_usd": 0.0}

    if price_usd is not None and prev_price is not None and prev_price > 0:
        delta_pct = (price_usd - prev_price) / prev_price
        delta_usd = delta_pct * float(args.notional_usd)
        if guard_active and delta_usd is not None:
            if delta_usd < 0:
                latest_cycle_impact["avoided_loss_usd"] = abs(delta_usd)
                avoided_loss_usd += abs(delta_usd)
            elif delta_usd > 0:
                latest_cycle_impact["missed_opportunity_usd"] = delta_usd
                missed_opportunity_usd += delta_usd

    payload = {
        "schema": "shadow_pnl_guardrail_v1",
        "generated_at_utc": _now_utc(),
        "policy": {
            "research_only": True,
            "not_for_trading_execution": True,
            "advisory_only": True,
        },
        "state": {
            "judge_decision": judge_decision,
            "decision_state": decision_state,
            "operator_action": operator_action,
            "guard_active": guard_active,
        },
        "price_context": {
            "current_price_usd": price_usd,
            "previous_price_usd": prev_price,
            "price_source": price_source,
            "delta_pct_vs_prev_cycle": delta_pct,
        },
        "impact": {
            "notional_usd": float(args.notional_usd),
            "delta_usd_vs_prev_cycle": delta_usd,
            "latest_cycle_impact": latest_cycle_impact,
            "cumulative_avoided_loss_usd": round(avoided_loss_usd, 6),
            "cumulative_missed_opportunity_usd": round(missed_opportunity_usd, 6),
        },
        "notes": [
            "Shadow metric only. No execution route is triggered from this artifact.",
            "Interpretation is conditional and for post-hoc governance review.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"guard_active={guard_active} price_source={price_source} current_price_usd={price_usd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

