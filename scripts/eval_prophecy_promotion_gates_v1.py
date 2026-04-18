# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.84, K:0.48, M:0.34}
# Balance: 90
# Purpose: B-track numeric gates before any prophecy feature promotion
# Keywords: prophecy, promotion, gates, walkforward, hypos
#!/usr/bin/env python3
"""Numeric promotion gates for B-track prophecy (measurement-only).

Evaluates **two** walk-forward families when artifacts exist:

1. **Per-date lens combo** — ``prophecy_per_date_combo_walkforward_v1_latest.json``
2. **Instrument combo** — ``prophecy_instrument_combo_walkforward_v1_latest.json``

Each uses the same aggregate thresholds (mean / stdev / beat-bull fraction / min fold).

Shared checks on ``btrack_prophecy_score_latest.json``:

- KOSPI + BTC row coverage per eval_date
- ``inputs.btc_csv`` present (score was built with a BTC CSV path)

``combined_all_passed`` requires every **evaluated** track to pass, including shared gates.
If the instrument walk-forward file is missing, the instrument track is **not** satisfied
(combined fails) so operators must run ``run_prophecy_instrument_combo_walkforward_v1.py``.

Use ``--fail-on-gate`` in CI to exit 1 when ``combined_all_passed`` is false.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LENS_WF = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_walkforward_v1_latest.json"
DEFAULT_INSTRUMENT_WF = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_walkforward_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_promotion_gates_v1_latest.json"
DEFAULT_STREAK_HISTORY = ROOT / "docs" / "final" / "artifacts" / "prophecy_promotion_strict_streak_v1.json"
SCHEMA = "prophecy_promotion_gates_v1"
VALID_DIR = {"bull", "bear", "neutral"}
SCHEMA_LENS_WF = "prophecy_per_date_combo_walkforward_v1"
SCHEMA_INSTRUMENT_WF = "prophecy_instrument_combo_walkforward_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _panel_dual_leg_gate(score_path: Path) -> dict[str, Any]:
    doc = _load_json(score_path)
    if not doc or not isinstance(doc.get("rows"), list):
        return {
            "gate_id": "panel_kospi_btc_per_date",
            "passed": False,
            "reason": "missing_or_invalid_score_json",
            "detail": {},
        }
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    by_date: dict[str, set[str]] = {}
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "").strip().lower()
        act = str(r.get("actual_direction") or "").strip().lower()
        if not ed or inst not in ("kospi", "btc") or act not in VALID_DIR:
            continue
        by_date.setdefault(ed, set()).add(inst)
    complete_dates = [d for d, legs in sorted(by_date.items()) if legs >= {"kospi", "btc"}]
    n_dates = len(by_date)
    n_complete = len(complete_dates)
    passed = n_complete == n_dates and n_dates > 0
    return {
        "gate_id": "panel_kospi_btc_per_date",
        "passed": passed,
        "reason": None if passed else "each_eval_date_must_have_kospi_and_btc_with_valid_actuals",
        "detail": {
            "n_eval_dates_with_any_row": n_dates,
            "n_eval_dates_with_kospi_and_btc": n_complete,
            "n_score_rows": len(rows),
        },
    }


def _score_btc_csv_input_gate(score_path: Path) -> dict[str, Any]:
    doc = _load_json(score_path) or {}
    inp = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
    raw = inp.get("btc_csv")
    has_path = raw is not None and str(raw).strip().lower() not in ("", "null", "none")
    return {
        "gate_id": "score_btc_csv_input_present",
        "passed": bool(has_path),
        "reason": None if has_path else "rebuild_score_with_btc_csv_hypothesis_multi",
        "detail": {"btc_csv": raw},
    }


def _walkforward_gates(
    wf: dict[str, Any],
    *,
    track_id: str,
    min_mean: float,
    max_stdev: float,
    min_beat_frac: float,
    min_worst_fold: float,
) -> list[dict[str, Any]]:
    agg = wf.get("aggregate") if isinstance(wf.get("aggregate"), dict) else {}
    folds = wf.get("folds") if isinstance(wf.get("folds"), list) else []

    mean_v = float(agg.get("mean_test_accuracy") or 0.0)
    stdev_v = float(agg.get("stdev_test_accuracy") or 0.0)
    beat_v = float(agg.get("fraction_test_beats_always_bull") or 0.0)
    min_fold = float(agg.get("min_test_accuracy") or 0.0)

    prefix = f"{track_id}_"
    gates: list[dict[str, Any]] = [
        {
            "gate_id": f"{prefix}wf_mean_test_accuracy",
            "passed": mean_v >= min_mean,
            "threshold": {"op": ">=", "min_mean_test_accuracy": min_mean},
            "observed": {"mean_test_accuracy": round(mean_v, 6)},
        },
        {
            "gate_id": f"{prefix}wf_stdev_test_accuracy",
            "passed": stdev_v <= max_stdev,
            "threshold": {"op": "<=", "max_stdev_test_accuracy": max_stdev},
            "observed": {"stdev_test_accuracy": round(stdev_v, 6)},
        },
        {
            "gate_id": f"{prefix}wf_fraction_folds_beat_always_bull",
            "passed": beat_v >= min_beat_frac,
            "threshold": {"op": ">=", "min_fraction_test_beats_always_bull": min_beat_frac},
            "observed": {"fraction_test_beats_always_bull": round(beat_v, 6), "n_folds": len(folds)},
        },
        {
            "gate_id": f"{prefix}wf_min_fold_test_accuracy",
            "passed": min_fold >= min_worst_fold,
            "threshold": {"op": ">=", "min_min_test_accuracy_across_folds": min_worst_fold},
            "observed": {"min_test_accuracy": round(min_fold, 6)},
        },
    ]
    return gates


def _all_true(gates: list[dict[str, Any]]) -> bool:
    return bool(gates) and all(bool(g.get("passed")) for g in gates)


def _load_history(path: Path) -> dict[str, Any]:
    doc = _load_json(path) or {}
    if not isinstance(doc, dict):
        doc = {}
    runs = doc.get("runs")
    if not isinstance(runs, list):
        runs = []
    return {"runs": runs}


def _save_history(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "prophecy_promotion_strict_streak_v1", "runs": runs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _strict_streak(runs: list[dict[str, Any]]) -> int:
    c = 0
    for r in reversed(runs):
        if bool(r.get("strict_passed")):
            c += 1
        else:
            break
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track prophecy promotion numeric gates (dual track + shared).")
    ap.add_argument(
        "--lens-walkforward-json",
        type=Path,
        default=DEFAULT_LENS_WF,
        help="Per-date lens combo walk-forward artifact.",
    )
    ap.add_argument(
        "--walkforward-json",
        type=Path,
        default=None,
        help="Deprecated alias for --lens-walkforward-json.",
    )
    ap.add_argument(
        "--instrument-walkforward-json",
        type=Path,
        default=DEFAULT_INSTRUMENT_WF,
        help="Instrument-combo walk-forward artifact (required for combined pass).",
    )
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument(
        "--promotion-track-mode",
        choices=("btc_only_crossassist", "dual"),
        default="btc_only_crossassist",
        help="btc_only_crossassist: evaluate lens track only (BTC target) + shared BTC input gate.",
    )
    ap.add_argument("--skip-shared-gates", action="store_true")
    ap.add_argument("--min-mean", type=float, default=0.55, dest="min_mean")
    ap.add_argument("--max-stdev", type=float, default=0.15, dest="max_stdev")
    ap.add_argument("--min-beat-bull-frac", type=float, default=0.5, dest="min_beat_frac")
    ap.add_argument("--min-worst-fold", type=float, default=0.4, dest="min_worst_fold")
    ap.add_argument("--soft-min-mean", type=float, default=0.45)
    ap.add_argument("--soft-max-stdev", type=float, default=0.22)
    ap.add_argument("--soft-min-beat-bull-frac", type=float, default=0.25)
    ap.add_argument("--soft-min-worst-fold", type=float, default=0.3)
    ap.add_argument("--strict-streak-required", type=int, default=5)
    ap.add_argument("--streak-history-json", type=Path, default=DEFAULT_STREAK_HISTORY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--fail-on-gate", action="store_true", help="Exit 1 when combined_all_passed is false.")
    args = ap.parse_args()

    lens_path = args.walkforward_json if args.walkforward_json is not None else args.lens_walkforward_json

    thresholds = {
        "min_mean_test_accuracy": args.min_mean,
        "max_stdev_test_accuracy": args.max_stdev,
        "min_fraction_test_beats_always_bull": args.min_beat_frac,
        "min_min_test_accuracy_across_folds": args.min_worst_fold,
    }
    soft_thresholds = {
        "min_mean_test_accuracy": args.soft_min_mean,
        "max_stdev_test_accuracy": args.soft_max_stdev,
        "min_fraction_test_beats_always_bull": args.soft_min_beat_bull_frac,
        "min_min_test_accuracy_across_folds": args.soft_min_worst_fold,
    }

    lens_wf = _load_json(lens_path) or {}
    lens_ok = str(lens_wf.get("schema") or "") == SCHEMA_LENS_WF
    lens_gates: list[dict[str, Any]] = []
    lens_passed = False
    if not lens_ok:
        lens_gates = [
            {
                "gate_id": "lens_artifact_valid",
                "passed": False,
                "reason": f"missing_or_invalid_lens_walkforward: {lens_path}",
                "detail": {},
            }
        ]
    else:
        lens_gates = _walkforward_gates(
            lens_wf,
            track_id="lens",
            min_mean=args.min_mean,
            max_stdev=args.max_stdev,
            min_beat_frac=args.min_beat_frac,
            min_worst_fold=args.min_worst_fold,
        )
        lens_passed = _all_true(lens_gates)

    inst_wf = _load_json(args.instrument_walkforward_json) or {}
    inst_ok = str(inst_wf.get("schema") or "") == SCHEMA_INSTRUMENT_WF
    inst_gates: list[dict[str, Any]] = []
    inst_passed = False
    if not inst_ok:
        inst_gates = [
            {
                "gate_id": "instrument_artifact_valid",
                "passed": False,
                "reason": f"missing_or_invalid_instrument_walkforward: {args.instrument_walkforward_json}",
                "detail": {},
            }
        ]
    else:
        inst_gates = _walkforward_gates(
            inst_wf,
            track_id="instrument",
            min_mean=args.min_mean,
            max_stdev=args.max_stdev,
            min_beat_frac=args.min_beat_frac,
            min_worst_fold=args.min_worst_fold,
        )
        inst_passed = _all_true(inst_gates)

    shared_gates: list[dict[str, Any]] = []
    shared_passed = True
    if not args.skip_shared_gates and args.score_json.is_file():
        if args.promotion_track_mode == "dual":
            shared_gates = [
                _panel_dual_leg_gate(args.score_json),
                _score_btc_csv_input_gate(args.score_json),
            ]
        else:
            # BTC-only promotion mode: require BTC source path, but not dual-leg panel completeness.
            shared_gates = [_score_btc_csv_input_gate(args.score_json)]
        shared_passed = _all_true(shared_gates)

    legacy_gates = list(lens_gates) + (shared_gates if not args.skip_shared_gates else [])
    shared_ok = True if args.skip_shared_gates else shared_passed
    if args.promotion_track_mode == "dual":
        combined_all_passed = bool(lens_passed and inst_passed and shared_ok)
    else:
        combined_all_passed = bool(lens_passed and shared_ok)
    strict_passed = combined_all_passed
    soft_lens_passed = False
    if lens_ok:
        soft_lens_passed = _all_true(
            _walkforward_gates(
                lens_wf,
                track_id="lens_soft_tmp",
                min_mean=float(soft_thresholds["min_mean_test_accuracy"]),
                max_stdev=float(soft_thresholds["max_stdev_test_accuracy"]),
                min_beat_frac=float(soft_thresholds["min_fraction_test_beats_always_bull"]),
                min_worst_fold=float(soft_thresholds["min_min_test_accuracy_across_folds"]),
            )
        )
    soft_passed = bool(soft_lens_passed and shared_ok)

    h = _load_history(args.streak_history_json)
    runs = list(h["runs"])
    runs.append(
        {
            "ts_utc": _utc_now(),
            "strict_passed": strict_passed,
            "soft_passed": soft_passed,
            "promotion_track_mode": args.promotion_track_mode,
            "strict_thresholds": thresholds,
            "soft_thresholds": soft_thresholds,
        }
    )
    if len(runs) > 200:
        runs = runs[-200:]
    _save_history(args.streak_history_json, runs)
    streak = _strict_streak(runs)
    auto_promote_ready = strict_passed and streak >= max(1, int(args.strict_streak_required))

    recommendation = "auto_promote_ready" if auto_promote_ready else ("manual_review_candidate" if strict_passed else "defer")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "lens_walkforward_json": str(lens_path),
            "instrument_walkforward_json": str(args.instrument_walkforward_json),
            "score_json": str(args.score_json),
            "promotion_track_mode": args.promotion_track_mode,
            "thresholds": thresholds,
            "soft_thresholds": soft_thresholds,
            "skip_shared_gates": bool(args.skip_shared_gates),
            "strict_streak_required": int(args.strict_streak_required),
            "streak_history_json": str(args.streak_history_json),
        },
        "tracks": {
            "per_date_lens": {
                "all_gates_passed": lens_passed,
                "gates": lens_gates,
            },
            "instrument_combo": {
                "all_gates_passed": inst_passed if args.promotion_track_mode == "dual" else None,
                "gates": inst_gates if args.promotion_track_mode == "dual" else [],
            },
            "shared": {
                "all_gates_passed": shared_passed if not args.skip_shared_gates else None,
                "gates": shared_gates,
            },
        },
        "gates": legacy_gates,
        "lens_all_gates_passed": lens_passed,
        "instrument_combo_all_gates_passed": inst_passed if args.promotion_track_mode == "dual" else None,
        "shared_all_gates_passed": shared_passed if not args.skip_shared_gates else None,
        "combined_all_passed": combined_all_passed,
        "all_gates_passed": combined_all_passed,
        "strict_passed": strict_passed,
        "soft_passed": soft_passed,
        "strict_pass_streak": streak,
        "auto_promote_ready": auto_promote_ready,
        "promotion_recommendation": recommendation,
        "note": "Dual-track B-track gates; combined requires lens WF + instrument WF + shared score checks. Human sign-off still required before A-track or live routing.",
    }

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")

    if args.fail_on_gate and not combined_all_passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
