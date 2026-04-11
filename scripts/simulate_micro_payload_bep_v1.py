#!/usr/bin/env python3
"""Micro-payload break-even batch size: N_BEP = Cost_fixed / (Gain - Cost_marginal).

Gain and Cost_marginal are per-packet byte budgets (same units as Cost_fixed).
When Gain <= Cost_marginal, no finite N achieves cumulative net positive vs fixed+variable.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "MICRO_PAYLOAD_BEP_SIM_V1.json"


def compute_bep(cost_fixed: float, gain: float, cost_marginal: float) -> dict:
    cf = max(0.0, float(cost_fixed))
    g = float(gain)
    cm = max(0.0, float(cost_marginal))
    margin = g - cm
    out: dict = {
        "cost_fixed_bytes": cf,
        "gain_per_unit_bytes": g,
        "cost_marginal_per_unit_bytes": cm,
        "contribution_margin_per_unit": margin,
    }
    if margin <= 0:
        out["n_bep"] = None
        out["n_bep_ceil"] = None
        out["status"] = "no_break_even"
        out["reason"] = "gain_per_unit <= cost_marginal_per_unit"
        return out
    n = cf / margin
    out["n_bep"] = n
    out["n_bep_ceil"] = int(math.ceil(n - 1e-12))
    out["status"] = "ok"
    return out


def sweep_curve(
    cost_fixed: float,
    gain: float,
    cost_marginal: float,
    *,
    n_max: int,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for n in range(0, max(0, int(n_max)) + 1):
        total_gain = n * gain
        total_cost = cost_fixed + n * cost_marginal
        net = total_gain - total_cost
        rows.append(
            {
                "n": float(n),
                "cumulative_gain_bytes": total_gain,
                "cumulative_cost_bytes": total_cost,
                "net_bytes": net,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="BEP batch size N = Cost_fixed / (Gain - Cost_marginal).")
    ap.add_argument("--cost-fixed", type=float, default=200.0, help="Fixed bytes (TLS/session/BLS budget, etc.).")
    ap.add_argument("--gain", type=float, default=50.0, help="Per-unit bytes saved (domain heuristic).")
    ap.add_argument("--cost-marginal", type=float, default=15.0, help="Per-unit variable bytes (framing, ids).")
    ap.add_argument(
        "--sweep-n-max",
        type=int,
        default=0,
        help="If >0, include 0..N cumulative gain/cost curve (for plotting).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-json", action="store_true", help="Print JSON to stdout instead of only file.")
    args = ap.parse_args()

    bep = compute_bep(args.cost_fixed, args.gain, args.cost_marginal)
    payload: dict = {
        "schema": "micro_payload_bep_sim_v1",
        "description": "N_BEP = Cost_fixed / (Gain - Cost_marginal); net at N is N*Gain - Cost_fixed - N*Cost_marginal.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "N_BEP = Cost_fixed / (Gain - Cost_marginal)",
        "bep": bep,
    }
    if int(args.sweep_n_max) > 0:
        ncap = int(args.sweep_n_max)
        if bep.get("n_bep_ceil") is not None:
            ncap = max(ncap, int(bep["n_bep_ceil"]) * 2)
        payload["curve_0_to_n"] = sweep_curve(
            float(args.cost_fixed),
            float(args.gain),
            float(args.cost_marginal),
            n_max=ncap,
        )

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    if args.stdout_json:
        sys.stdout.write(text)
    else:
        print("OK:", out_path)
        print("status:", bep.get("status"))
        if bep.get("n_bep_ceil") is not None:
            print("N_BEP (ceil):", bep["n_bep_ceil"], "exact:", bep.get("n_bep"))
        else:
            print("N_BEP: undefined —", bep.get("reason", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
