#!/usr/bin/env python3
"""Apply active sasang veto-only config to trading execution proposal."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROPOSAL = ROOT / "reports" / "trading_execution_proposal_latest.json"
DEFAULT_VETO_CFG = ROOT / "docs" / "final" / "artifacts" / "sasang_veto_only_active_config_latest.json"
DEFAULT_OUT = ROOT / "reports" / "trading_execution_proposal_veto_adjusted_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


_BTC_SYMBOL_ALIASES = frozenset({"BTCUSDT", "BTC-USD", "BTCUSD", "XBTUSDT"})


def _resolve_veto_branch_id(symbol: str, veto_cfg: dict[str, Any]) -> str:
    sym = str(symbol or "").strip().upper().replace(" ", "")
    routing = veto_cfg.get("symbol_routing")
    if isinstance(routing, dict) and sym in routing:
        bid = str(routing[sym]).strip()
        if bid:
            return bid
    if sym in _BTC_SYMBOL_ALIASES:
        return "BTCUSDT"
    return "default"


def _resolve_soft_exposure(symbol: str, veto_cfg: dict[str, Any]) -> tuple[float, str]:
    branches = veto_cfg.get("asset_branches")
    if isinstance(branches, dict) and branches:
        bid = _resolve_veto_branch_id(symbol, veto_cfg)
        if bid not in branches or not isinstance(branches.get(bid), dict):
            bid = "default"
        br = branches.get(bid)
        if isinstance(br, dict) and "soft_exposure" in br:
            return float(br.get("soft_exposure") or 1.0), bid
    return float(veto_cfg.get("soft_exposure", 1.0) or 1.0), "legacy_top_level"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proposal-json", type=Path, default=DEFAULT_PROPOSAL)
    ap.add_argument("--veto-config-json", type=Path, default=DEFAULT_VETO_CFG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    proposal = _read_json(args.proposal_json)
    if proposal.get("schema") != "trading_execution_proposal_v1":
        raise SystemExit("invalid/missing trading_execution_proposal_v1")

    veto_cfg = _read_json(args.veto_config_json)
    enabled = bool(veto_cfg.get("enabled")) and str(veto_cfg.get("scope")) == "veto_only_non_directional"

    order = proposal.get("order_intent") if isinstance(proposal.get("order_intent"), dict) else {}
    sym = str(order.get("symbol") or "")
    soft_exposure, veto_branch_id = _resolve_soft_exposure(sym, veto_cfg)
    soft_exposure = _clamp(soft_exposure, 0.0, 1.0)

    raw_qty = float(order.get("qty", 0.0) or 0.0)
    effective_qty = raw_qty * soft_exposure if enabled else raw_qty
    effective_qty = round(effective_qty, 10)

    adjusted = {
        "schema": "trading_execution_proposal_veto_adjusted_v1",
        "generated_at_utc": _now(),
        "base_proposal_ref": str(args.proposal_json).replace("\\", "/"),
        "veto_config_ref": str(args.veto_config_json).replace("\\", "/"),
        "veto_applied": enabled,
        "soft_exposure": soft_exposure,
        "veto_branch_id": veto_branch_id,
        "order_adjustment": {
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "raw_qty": raw_qty,
            "effective_qty": effective_qty,
        },
        "guardrails": {
            "directional_entry_disabled": bool((veto_cfg.get("hard_guardrails") or {}).get("directional_entry_disabled")),
            "auto_bridge_allowed": bool((veto_cfg.get("hard_guardrails") or {}).get("auto_bridge_allowed")),
        },
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(adjusted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"VETO_APPLIED={enabled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
