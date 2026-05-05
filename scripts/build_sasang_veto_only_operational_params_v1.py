#!/usr/bin/env python3
"""Build operational veto-only parameter candidate from soft-veto sweep best_feasible."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
SWEEP_JSON = ART / "sasang_daily_regime_threshold_sweep_soft_veto_v1_latest.json"
BTC_TUNED_SWEEP_JSON = ART / "sasang_daily_regime_threshold_sweep_soft_veto_btc7y_tuned_latest.json"
STEP5_JSON = ART / "sasang_12state_promotion_decision_step5_latest.json"
OUT_JSON = ART / "sasang_veto_only_operational_params_v1_latest.json"
ACTIVE_JSON = ART / "sasang_veto_only_active_config_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _best_from_sweep(sweep: dict[str, Any]) -> dict[str, Any] | None:
    best = sweep.get("best_feasible")
    if isinstance(best, dict):
        return best
    feasible = sweep.get("feasible_top20") if isinstance(sweep.get("feasible_top20"), list) else []
    if feasible and isinstance(feasible[0], dict):
        return feasible[0]
    top20 = sweep.get("best_top20") if isinstance(sweep.get("best_top20"), list) else []
    if top20 and isinstance(top20[0], dict):
        return top20[0]
    return None


def _candidate_branch_slice(best: dict[str, Any], sweep_ref: str) -> dict[str, Any]:
    return {
        "input_sweep_ref": sweep_ref.replace("\\", "/"),
        "veto_set": best.get("veto_set"),
        "soft_exposure": best.get("soft_exposure"),
        "params": best.get("params"),
        "metrics": {
            "veto_total_return": best.get("veto_total_return"),
            "buyhold_total_return": best.get("buyhold_total_return"),
            "mdd_delta": best.get("mdd_delta"),
            "cvar95_delta": best.get("cvar95_delta"),
            "active_ratio": best.get("active_ratio"),
        },
        "gates": {
            "pass_mdd": best.get("pass_mdd"),
            "pass_cvar": best.get("pass_cvar"),
            "pass_return_floor": best.get("pass_return_floor"),
        },
    }


def _active_branch_slice(best: dict[str, Any]) -> dict[str, Any]:
    return {
        "veto_set": best.get("veto_set"),
        "soft_exposure": best.get("soft_exposure"),
        "params": best.get("params"),
    }


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_JSON)
    ap.add_argument(
        "--btc-tuned-sweep-json",
        type=Path,
        default=BTC_TUNED_SWEEP_JSON,
        help="Optional BTC 7y tuned soft-veto sweep; merged into asset_branches.BTCUSDT when valid.",
    )
    ap.add_argument("--step5-json", type=Path, default=STEP5_JSON)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--active-json", type=Path, default=ACTIVE_JSON)
    args = ap.parse_args()

    sweep = _safe_json(args.sweep_json)
    step5 = _safe_json(args.step5_json)
    if sweep.get("schema") != "sasang_daily_regime_threshold_sweep_soft_veto_v1":
        raise SystemExit("invalid sweep schema")
    if step5.get("schema") != "sasang_12state_promotion_decision_step5_v1":
        raise SystemExit("invalid step5 schema")

    best_default = _best_from_sweep(sweep)
    if not isinstance(best_default, dict):
        raise SystemExit("no feasible candidate in default sweep artifact")

    btc_sweep = _safe_json(args.btc_tuned_sweep_json)
    best_btc = _best_from_sweep(btc_sweep) if btc_sweep.get("schema") == "sasang_daily_regime_threshold_sweep_soft_veto_v1" else None

    decision = str(step5.get("decision", ""))
    veto_active = decision == "GATING_VETO_ONLY_ACTIVE_WITH_HUMAN_APPROVAL"
    gating_scope = str(step5.get("gating_scope", ""))

    input_refs: dict[str, str] = {
        "sweep": str(args.sweep_json).replace("\\", "/"),
        "step5": str(args.step5_json).replace("\\", "/"),
    }
    if best_btc:
        input_refs["btc_tuned_sweep"] = str(args.btc_tuned_sweep_json).replace("\\", "/")

    asset_branches: dict[str, Any] = {
        "default": _candidate_branch_slice(best_default, str(args.sweep_json)),
    }
    symbol_routing: dict[str, str] = {}
    if best_btc:
        asset_branches["BTCUSDT"] = _candidate_branch_slice(best_btc, str(args.btc_tuned_sweep_json))
        symbol_routing = {"BTCUSDT": "BTCUSDT", "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT", "XBTUSDT": "BTCUSDT"}

    candidate = {
        "schema": "sasang_veto_only_operational_params_v1",
        "generated_at_utc": _now(),
        "input_refs": input_refs,
        "eligibility": {
            "decision": decision,
            "veto_active": veto_active,
            "gating_scope": gating_scope,
            "directional_auto_bridge_allowed": bool(step5.get("auto_bridge_allowed", False)),
        },
        "selected_candidate": {
            "veto_set": best_default.get("veto_set"),
            "soft_exposure": best_default.get("soft_exposure"),
            "params": best_default.get("params"),
            "metrics": {
                "veto_total_return": best_default.get("veto_total_return"),
                "buyhold_total_return": best_default.get("buyhold_total_return"),
                "mdd_delta": best_default.get("mdd_delta"),
                "cvar95_delta": best_default.get("cvar95_delta"),
                "active_ratio": best_default.get("active_ratio"),
            },
            "gates": {
                "pass_mdd": best_default.get("pass_mdd"),
                "pass_cvar": best_default.get("pass_cvar"),
                "pass_return_floor": best_default.get("pass_return_floor"),
            },
        },
        "asset_branches": asset_branches,
        "symbol_routing": symbol_routing,
        "policy_note": "Use as veto-only exposure modulation; directional triggering remains disabled.",
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    args.out_json.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    active_branches: dict[str, Any] = {"default": _active_branch_slice(best_default)}
    if best_btc:
        active_branches["BTCUSDT"] = _active_branch_slice(best_btc)

    active_cfg = {
        "schema": "sasang_veto_only_active_config_v1",
        "generated_at_utc": _now(),
        "enabled": veto_active,
        "scope": "veto_only_non_directional",
        "veto_set": best_default.get("veto_set"),
        "soft_exposure": best_default.get("soft_exposure"),
        "params": best_default.get("params"),
        "asset_branches": active_branches,
        "symbol_routing": symbol_routing,
        "source_candidate_ref": str(args.out_json).replace("\\", "/"),
        "hard_guardrails": {
            "directional_entry_disabled": True,
            "auto_bridge_allowed": False,
            "most_conservative_wins": True,
        },
    }
    args.active_json.write_text(json.dumps(active_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_json}")
    print(f"WROTE: {args.active_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
