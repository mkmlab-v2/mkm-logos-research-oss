# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Falsification gate for survivor crash correlation backtest outputs.
# Keywords: gate, falsification, correlation, pvalue, hold
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKTEST_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_survivor_crash_correlation_backtest_latest.json"
DEFAULT_OUTPUT_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_survivor_crash_falsification_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _asset_gate(
    asset_doc: dict[str, Any],
    min_abs_corr: float,
    max_pvalue: float,
    min_n: int,
    objective_mode: str,
    blend_alpha: float,
) -> dict[str, Any]:
    best = asset_doc.get("best_abs_corr_row") if isinstance(asset_doc.get("best_abs_corr_row"), dict) else {}
    return_corr = _safe_float(best.get("return_corr"))
    crash_corr = _safe_float(best.get("crash_flag_corr"))
    return_n = int(best.get("return_n") or 0)
    crash_n = int(best.get("crash_flag_n") or 0)
    if objective_mode == "crash":
        objective_corr = crash_corr
        objective_n = crash_n
    elif objective_mode == "blended":
        r_abs = abs(return_corr) if return_corr is not None else 0.0
        c_abs = abs(crash_corr) if crash_corr is not None else 0.0
        sign = 1.0 if (return_corr or 0.0) >= 0 else -1.0
        objective_corr = sign * (blend_alpha * r_abs + (1.0 - blend_alpha) * c_abs)
        objective_n = min(return_n, crash_n) if return_n and crash_n else max(return_n, crash_n)
    else:
        objective_corr = return_corr
        objective_n = return_n

    p = _safe_float(asset_doc.get("best_return_corr_permutation_pvalue"))
    pass_abs_corr = objective_corr is not None and abs(objective_corr) >= min_abs_corr
    pass_p = p is not None and p <= max_pvalue
    pass_n = objective_n >= min_n
    passed = bool(pass_abs_corr and pass_p and pass_n)
    return {
        "passed": passed,
        "objective_mode": objective_mode,
        "objective_corr": objective_corr,
        "objective_corr_abs": abs(objective_corr) if objective_corr is not None else None,
        "objective_n": objective_n,
        "best_return_corr": return_corr,
        "best_crash_flag_corr": crash_corr,
        "best_return_corr_n": return_n,
        "best_crash_flag_corr_n": crash_n,
        "best_return_corr_permutation_pvalue": p,
        "checks": {
            "abs_corr_gte_threshold": pass_abs_corr,
            "pvalue_lte_threshold": pass_p,
            "n_gte_threshold": pass_n,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate falsification gate from survivor crash-correlation backtest.")
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST_JSON)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    ap.add_argument("--min-abs-corr", type=float, default=0.5)
    ap.add_argument("--max-pvalue", type=float, default=0.05)
    ap.add_argument("--min-n", type=int, default=250)
    ap.add_argument("--objective-mode", choices=("return", "crash", "blended"), default="return")
    ap.add_argument("--blend-alpha", type=float, default=0.5, help="Used when objective-mode=blended; weight on return corr.")
    args = ap.parse_args()

    doc = _read_json(args.backtest_json)
    analysis = doc.get("analysis") if isinstance(doc.get("analysis"), dict) else {}
    blend_alpha = max(0.0, min(1.0, float(args.blend_alpha)))
    kospi = _asset_gate(
        analysis.get("kospi") if isinstance(analysis.get("kospi"), dict) else {},
        args.min_abs_corr,
        args.max_pvalue,
        args.min_n,
        args.objective_mode,
        blend_alpha,
    )
    btc = _asset_gate(
        analysis.get("btc") if isinstance(analysis.get("btc"), dict) else {},
        args.min_abs_corr,
        args.max_pvalue,
        args.min_n,
        args.objective_mode,
        blend_alpha,
    )
    any_pass = bool(kospi["passed"] or btc["passed"])
    decision = "GO_RESEARCH_SIGNAL_CANDIDATE" if any_pass else "HOLD_RESEARCH_ONLY"

    out = {
        "schema": "btrack_survivor_crash_falsification_gate_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "input_backtest_json": str(args.backtest_json),
        "thresholds": {
            "min_abs_corr": float(args.min_abs_corr),
            "max_pvalue": float(args.max_pvalue),
            "min_n": int(args.min_n),
            "objective_mode": args.objective_mode,
            "blend_alpha": blend_alpha,
        },
        "asset_checks": {
            "kospi": kospi,
            "btc": btc,
        },
        "result": {
            "passed_any_asset": any_pass,
            "decision": decision,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(f"decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
