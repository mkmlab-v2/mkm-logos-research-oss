# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.84, K:0.52, M:0.38}
# Balance: 88
# Purpose: One-shot B-track score + dual walk-forward + promotion gates (reports paths)
# Keywords: prophecy, btrack, walkforward, promotion, chain
#!/usr/bin/env python3
"""B-track recommended eval chain (measurement-only): dual-leg score → walk-forwards + promotion gates.

1. Builds ``btrack_prophecy_score`` with **KOSPI+BTC dual-leg panel** (``--force-dual-leg-panel``),
   mild ``downside_force_bear`` (optional) and tunable ``--neutral-bps`` (default 2.0 from sweep).
2. Runs **per-date lens combo** blocked walk-forward (BTC target).
3. Runs **instrument-combo** blocked walk-forward (same score panel).
4. Runs ``eval_prophecy_promotion_gates_v1`` in ``dual`` mode (lens + instrument + shared gates).

Optional **``--neutral-bps-sweep``** (comma-separated floats): repeats the full chain per value,
writes artifacts under ``--sweep-dir`` (isolated streak file so production streak is not spammed),
and emits ``--sweep-summary-json`` with one row per ``neutral_bps`` (strict/soft flags + WF means).

**``--auto-sweep-and-apply``**: one flag runs ``--auto-sweep-grid`` (default ``2,2.5,3,4,6``) sweep then
copies the mean-best row to ``*_latest`` (same as ``--apply-best-sweep-row-to-latest``). Do not combine
with ``--neutral-bps-sweep``.

**``--apply-best-sweep-row-to-latest``** (after a sweep): reads ``--sweep-summary-json``, picks
``best_neutral_bps_by_lens_then_instrument_mean``, copies that row's score + walk-forward JSON into
the default ``reports/*_latest.json`` paths, then re-runs ``eval_prophecy_promotion_gates_v1`` once
with ``--streak-history-json`` so production streak stays coherent (no full rebuild).

Outputs default to ``reports/`` so canonical ``docs/final/artifacts/*_latest.json`` paths are not
overwritten. Streak history defaults to ``reports/…`` so operator streak files under
``docs/final/artifacts/`` stay untouched unless ``--streak-history-json`` is set.

B-track / [HYPO] / research_only — not a live order trigger.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"
LENS_WF = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"
INST_WF = ROOT / "scripts" / "run_prophecy_instrument_combo_walkforward_v1.py"
GATES = ROOT / "scripts" / "eval_prophecy_promotion_gates_v1.py"
BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
HYPO = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"

DEFAULT_SCORE_OUT = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_LENS_OUT = ROOT / "reports" / "prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_INST_OUT = ROOT / "reports" / "prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_GATES_OUT = ROOT / "reports" / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
DEFAULT_SUMMARY_OUT = ROOT / "reports" / "prophecy_btrack_recommended_eval_chain_summary_v1_latest.json"
DEFAULT_STREAK = ROOT / "reports" / "prophecy_promotion_strict_streak_recommended_chain_v1.json"
DEFAULT_SWEEP_DIR = ROOT / "reports" / "prophecy_btrack_recommended_nbps_sweep_v1"
DEFAULT_SWEEP_SUMMARY = ROOT / "reports" / "prophecy_btrack_recommended_nbps_sweep_v1_latest.json"
DEFAULT_AUTO_SWEEP_GRID = "2,2.5,3,4,6"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _mild_downside_args() -> list[str]:
    return [
        "--downside-force-bear-enable",
        "--downside-force-bear-lookback",
        "5",
        "--downside-force-bear-min-down-days",
        "3",
        "--downside-force-bear-min-cum-down-pct",
        "4.5",
    ]


def parse_neutral_bps_sweep_csv(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.replace(";", ",").split(","):
        p = part.strip()
        if not p:
            continue
        out.append(float(p))
    return out


def _nb_slug(nb: float) -> str:
    return str(nb).replace(".", "_")


def _rel_workspace(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _gate_mean(doc: dict[str, Any] | None, *, track: str, gate_id: str) -> float | None:
    if not isinstance(doc, dict):
        return None
    tr = doc.get("tracks") or {}
    block = tr.get(track) if isinstance(tr, dict) else None
    if not isinstance(block, dict):
        return None
    gates = block.get("gates")
    if not isinstance(gates, list):
        return None
    for g in gates:
        if not isinstance(g, dict):
            continue
        if g.get("gate_id") == gate_id:
            obs = g.get("observed") or {}
            if isinstance(obs, dict):
                v = obs.get("mean_test_accuracy")
                if isinstance(v, (int, float)):
                    return float(v)
            return None
    return None


class _ChainPaths(NamedTuple):
    score_json: Path
    lens_out: Path
    inst_out: Path
    gates_out: Path
    streak_json: Path


def _run_one_recommended_eval(
    *,
    neutral_bps: float,
    paths: _ChainPaths,
    recent_trading_days: int,
    n_folds: int,
    hypothesis_json: Path,
    btc_csv: Path,
    no_mild_downside: bool,
    skip_gates: bool,
    fail_on_gate: bool,
    calibration_note: str,
    per_date_direction_json: Path | None = None,
    include_source_direction_signal: bool = False,
    include_expanded_prior_features: bool = False,
) -> tuple[int, list[dict[str, object]], dict[str, Any] | None]:
    score_path = paths.score_json
    score_path.parent.mkdir(parents=True, exist_ok=True)

    build_cmd: list[str] = [
        sys.executable,
        str(BUILD),
        "--hypothesis-json",
        str(hypothesis_json),
        "--btc-csv",
        str(btc_csv),
        "--force-dual-leg-panel",
        "--recent-trading-days",
        str(max(1, int(recent_trading_days))),
        "--neutral-bps",
        str(float(neutral_bps)),
        "--output",
        str(score_path),
    ]
    if not no_mild_downside:
        build_cmd.extend(_mild_downside_args())
    if per_date_direction_json is not None:
        build_cmd.extend(["--per-date-direction-json", str(per_date_direction_json)])

    steps: list[dict[str, object]] = []
    rc = _run(build_cmd)
    steps.append({"step": "build_btrack_prophecy_score", "exit_code": rc, "cmd": build_cmd})
    if rc != 0:
        return rc, steps, None

    n_folds_clamped = max(2, int(n_folds))

    lens_cmd = [
        sys.executable,
        str(LENS_WF),
        "--score-json",
        str(score_path),
        "--btc-csv",
        str(btc_csv),
        "--n-folds",
        str(n_folds_clamped),
        "--output",
        str(paths.lens_out),
    ]
    if include_source_direction_signal:
        lens_cmd.append("--include-source-direction-signal")
    if include_expanded_prior_features:
        lens_cmd.append("--include-expanded-prior-features")
    rc = _run(lens_cmd)
    steps.append({"step": "run_prophecy_per_date_combo_walkforward", "exit_code": rc, "cmd": lens_cmd})
    if rc != 0:
        return rc, steps, None

    inst_cmd = [
        sys.executable,
        str(INST_WF),
        "--score-json",
        str(score_path),
        "--btc-csv",
        str(btc_csv),
        "--n-folds",
        str(n_folds_clamped),
        "--output",
        str(paths.inst_out),
    ]
    rc = _run(inst_cmd)
    steps.append({"step": "run_prophecy_instrument_combo_walkforward", "exit_code": rc, "cmd": inst_cmd})
    if rc != 0:
        return rc, steps, None

    if skip_gates:
        return 0, steps, None

    gates_cmd = [
        sys.executable,
        str(GATES),
        "--promotion-track-mode",
        "dual",
        "--lens-walkforward-json",
        str(paths.lens_out),
        "--instrument-walkforward-json",
        str(paths.inst_out),
        "--score-json",
        str(score_path),
        "--hypothesis-json",
        str(hypothesis_json),
        "--streak-history-json",
        str(paths.streak_json),
        "--output",
        str(paths.gates_out),
        "--calibration-note",
        calibration_note,
    ]
    if fail_on_gate:
        gates_cmd.append("--fail-on-gate")

    rc = _run(gates_cmd)
    steps.append({"step": "eval_prophecy_promotion_gates", "exit_code": rc, "cmd": gates_cmd})

    gates_payload: dict[str, Any] | None = None
    if paths.gates_out.is_file():
        try:
            gates_payload = json.loads(paths.gates_out.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            gates_payload = None

    return rc, steps, gates_payload


def _write_summary(
    path: Path, steps: list[dict[str, object]], *, gates: dict | None, neutral_bps: float | None = None
) -> None:
    combined = None
    rec = None
    soft = None
    lens_soft = None
    inst_soft = None
    if isinstance(gates, dict):
        combined = gates.get("combined_all_passed")
        rec = gates.get("promotion_recommendation")
        soft = gates.get("soft_passed")
        lens_soft = gates.get("lens_soft_passed")
        inst_soft = gates.get("instrument_soft_passed")
    all_ok = all(s.get("exit_code") == 0 for s in steps)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema": "prophecy_btrack_recommended_eval_chain_summary_v1",
        "generated_at_utc": _utc_now(),
        "all_steps_exit_zero": all_ok,
        "combined_all_passed": combined,
        "promotion_recommendation": rec,
        "steps": steps,
    }
    if soft is not None:
        payload["soft_passed"] = soft
    if lens_soft is not None:
        payload["lens_soft_passed"] = lens_soft
    if inst_soft is not None:
        payload["instrument_soft_passed"] = inst_soft
    if neutral_bps is not None:
        payload["neutral_bps"] = float(neutral_bps)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {path.resolve()}")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def apply_best_sweep_row_to_latest(
    *,
    sweep_summary_json: Path,
    sweep_dir_fallback: Path,
    score_json: Path,
    lens_out: Path,
    inst_out: Path,
    gates_out: Path,
    summary_out: Path,
    hypothesis_json: Path,
    streak_history_json: Path,
) -> int:
    """Copy sweep mean-best row artifacts to default latest paths; re-eval gates on prod streak."""
    doc = _load_json(sweep_summary_json)
    if not doc or str(doc.get("schema") or "") != "prophecy_btrack_recommended_nbps_sweep_v1":
        print(f"Missing or invalid sweep summary: {sweep_summary_json}", file=sys.stderr)
        return 2
    best = doc.get("best_neutral_bps_by_lens_then_instrument_mean")
    if best is None:
        print("Sweep summary has no best_neutral_bps_by_lens_then_instrument_mean.", file=sys.stderr)
        return 2
    nb = float(best)
    slug = _nb_slug(nb)
    inp = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
    raw_dir = inp.get("sweep_dir") if isinstance(inp, dict) else None
    sweep_dir = Path(str(raw_dir)).resolve() if raw_dir else sweep_dir_fallback.resolve()
    src = _ChainPaths(
        score_json=sweep_dir / f"btrack_prophecy_score_recommended_nbps_{slug}.json",
        lens_out=sweep_dir / f"prophecy_per_date_combo_walkforward_recommended_nbps_{slug}.json",
        inst_out=sweep_dir / f"prophecy_instrument_combo_walkforward_recommended_nbps_{slug}.json",
        gates_out=sweep_dir / f"prophecy_promotion_gates_recommended_nbps_{slug}.json",
        streak_json=streak_history_json,
    )
    for label, p in (
        ("score", src.score_json),
        ("lens_wf", src.lens_out),
        ("instrument_wf", src.inst_out),
    ):
        if not p.is_file():
            print(f"Missing sweep {label} artifact: {p}", file=sys.stderr)
            return 2
    score_json.parent.mkdir(parents=True, exist_ok=True)
    lens_out.parent.mkdir(parents=True, exist_ok=True)
    inst_out.parent.mkdir(parents=True, exist_ok=True)
    gates_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src.score_json, score_json)
    shutil.copy2(src.lens_out, lens_out)
    shutil.copy2(src.inst_out, inst_out)
    note = (
        f"recommended_chain_v1 apply_best_sweep_row neutral_bps={nb}; "
        "copied score+wfs from sweep; gates re-eval on prod streak."
    )
    gates_cmd = [
        sys.executable,
        str(GATES),
        "--promotion-track-mode",
        "dual",
        "--lens-walkforward-json",
        str(lens_out),
        "--instrument-walkforward-json",
        str(inst_out),
        "--score-json",
        str(score_json),
        "--hypothesis-json",
        str(hypothesis_json),
        "--streak-history-json",
        str(streak_history_json),
        "--output",
        str(gates_out),
        "--calibration-note",
        note,
    ]
    rc = _run(gates_cmd)
    steps: list[dict[str, object]] = [
        {
            "step": "apply_best_sweep_row_copy_score_wf",
            "exit_code": 0,
            "cmd": ["shutil.copy2", str(src.score_json), str(score_json)],
        },
        {
            "step": "eval_prophecy_promotion_gates_after_sweep_apply",
            "exit_code": rc,
            "cmd": gates_cmd,
        },
    ]
    gates_payload = _load_json(gates_out)
    _write_summary(summary_out, steps, gates=gates_payload, neutral_bps=nb)
    print(f"Applied sweep best row neutral_bps={nb} -> latest paths.", file=sys.stderr)
    return rc


def _ensure_isolated_streak(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(
            json.dumps({"schema": "prophecy_promotion_strict_streak_v1", "runs": []}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument(
        "--neutral-bps-sweep",
        default="",
        metavar="CSV",
        help="Comma-separated neutral_bps values; runs isolated sweep under --sweep-dir and writes --sweep-summary-json.",
    )
    ap.add_argument(
        "--sweep-dir",
        type=Path,
        default=DEFAULT_SWEEP_DIR,
        help="Directory for per-nbps score/wf/gates artifacts (sweep mode only).",
    )
    ap.add_argument(
        "--sweep-summary-json",
        type=Path,
        default=DEFAULT_SWEEP_SUMMARY,
        help="Aggregate sweep report path (sweep mode only).",
    )
    ap.add_argument(
        "--sweep-promote-best-to-latest",
        action="store_true",
        help="If any sweep row has combined_all_passed, re-run the first such neutral_bps into default *_latest.json paths.",
    )
    ap.add_argument(
        "--apply-best-sweep-row-to-latest",
        action="store_true",
        help="After sweep (or standalone): copy best_neutral_bps row to default latest paths + re-eval gates on prod streak.",
    )
    ap.add_argument(
        "--auto-sweep-and-apply",
        action="store_true",
        help="Run default neutral_bps sweep (--auto-sweep-grid) then apply best row to *_latest (do not pass --neutral-bps-sweep).",
    )
    ap.add_argument(
        "--auto-sweep-grid",
        default=DEFAULT_AUTO_SWEEP_GRID,
        metavar="CSV",
        help=f"Comma-separated grid for --auto-sweep-and-apply only (default {DEFAULT_AUTO_SWEEP_GRID}).",
    )
    ap.add_argument("--no-mild-downside", action="store_true", help="Omit downside_force_bear mild block.")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_OUT)
    ap.add_argument("--lens-walkforward-out", type=Path, default=DEFAULT_LENS_OUT)
    ap.add_argument("--instrument-walkforward-out", type=Path, default=DEFAULT_INST_OUT)
    ap.add_argument("--gates-out", type=Path, default=DEFAULT_GATES_OUT)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY_OUT)
    ap.add_argument(
        "--streak-history-json",
        type=Path,
        default=DEFAULT_STREAK,
        help="Append-only streak log for eval_prophecy_promotion_gates_v1 (use reports/ default).",
    )
    ap.add_argument("--hypothesis-json", type=Path, default=HYPO)
    ap.add_argument("--btc-csv", type=Path, default=BTC_CSV)
    ap.add_argument(
        "--skip-gates",
        action="store_true",
        help="Stop after walk-forwards (no eval_prophecy_promotion_gates_v1).",
    )
    ap.add_argument(
        "--fail-on-gate",
        action="store_true",
        help="Pass --fail-on-gate to eval (exit 1 when combined_all_passed is false).",
    )
    ap.add_argument(
        "--per-date-direction-json",
        type=Path,
        default=None,
        help="V2 lane: per-date predicted_direction map for score build.",
    )
    ap.add_argument(
        "--per-date-min-confidence",
        type=float,
        default=None,
        help="Accepted for ensemble_v2_eval_chain CLI compatibility (filtering is in direction builder).",
    )
    ap.add_argument("--include-source-direction-signal", action="store_true")
    ap.add_argument("--include-expanded-prior-features", action="store_true")
    ap.add_argument(
        "--instrument-btc-policies",
        default="",
        help="Accepted for v2 eval_chain compatibility (instrument WF uses score panel).",
    )
    ap.add_argument("--instrument-include-panel-kospi-mode", action="store_true")
    ap.add_argument("--instrument-adaptive-panel-or-joint", action="store_true")
    ap.add_argument("--instrument-train-holdout-select", action="store_true")
    ap.add_argument("--instrument-beat-bull-train-weight", type=float, default=None)
    ap.add_argument("--instrument-force-panel-policy", action="store_true")
    ap.add_argument(
        "--calibration-note",
        default="",
        help="Override default calibration note on promotion gates eval.",
    )
    args = ap.parse_args()

    if not args.btc_csv.is_file():
        print(f"Missing BTC CSV: {args.btc_csv}", file=sys.stderr)
        return 2

    auto_apply_after_sweep = False
    if bool(getattr(args, "auto_sweep_and_apply", False)):
        if str(args.neutral_bps_sweep or "").strip():
            print("Do not pass --neutral-bps-sweep with --auto-sweep-and-apply.", file=sys.stderr)
            return 2
        sweep_raw = str(args.auto_sweep_grid or "").strip() or DEFAULT_AUTO_SWEEP_GRID
        auto_apply_after_sweep = True
    else:
        sweep_raw = str(args.neutral_bps_sweep or "").strip()

    if args.apply_best_sweep_row_to_latest and not sweep_raw:
        return apply_best_sweep_row_to_latest(
            sweep_summary_json=args.sweep_summary_json,
            sweep_dir_fallback=args.sweep_dir,
            score_json=args.score_json,
            lens_out=args.lens_walkforward_out,
            inst_out=args.instrument_walkforward_out,
            gates_out=args.gates_out,
            summary_out=args.summary_out,
            hypothesis_json=args.hypothesis_json,
            streak_history_json=args.streak_history_json,
        )

    if sweep_raw:
        grid = parse_neutral_bps_sweep_csv(sweep_raw)
        if not grid:
            print("Empty --neutral-bps-sweep after parsing.", file=sys.stderr)
            return 2
        sweep_dir: Path = args.sweep_dir
        sweep_dir.mkdir(parents=True, exist_ok=True)
        streak_iso = sweep_dir / "promotion_strict_streak_isolated_sweep_v1.json"
        _ensure_isolated_streak(streak_iso)

        rows: list[dict[str, Any]] = []
        any_strict = False
        first_promote_nb: float | None = None

        for nb in grid:
            slug = _nb_slug(nb)
            paths = _ChainPaths(
                score_json=sweep_dir / f"btrack_prophecy_score_recommended_nbps_{slug}.json",
                lens_out=sweep_dir / f"prophecy_per_date_combo_walkforward_recommended_nbps_{slug}.json",
                inst_out=sweep_dir / f"prophecy_instrument_combo_walkforward_recommended_nbps_{slug}.json",
                gates_out=sweep_dir / f"prophecy_promotion_gates_recommended_nbps_{slug}.json",
                streak_json=streak_iso,
            )
            note = (
                f"recommended_chain_v1 sweep neutral_bps={nb}; dual-leg + mild_downside; "
                "reports subdir; isolated streak."
            )
            rc, _steps, gates = _run_one_recommended_eval(
                neutral_bps=nb,
                paths=paths,
                recent_trading_days=int(args.recent_trading_days),
                n_folds=int(args.n_folds),
                hypothesis_json=args.hypothesis_json,
                btc_csv=args.btc_csv,
                no_mild_downside=bool(args.no_mild_downside),
                skip_gates=bool(args.skip_gates),
                fail_on_gate=bool(args.fail_on_gate),
                calibration_note=note,
            )
            comb = bool(gates.get("combined_all_passed")) if isinstance(gates, dict) else False
            if comb:
                any_strict = True
                if first_promote_nb is None:
                    first_promote_nb = nb
            row: dict[str, Any] = {
                "neutral_bps": nb,
                "all_steps_exit_zero": rc == 0,
                "exit_code": rc,
                "score_json": _rel_workspace(paths.score_json),
                "gates_json": _rel_workspace(paths.gates_out),
                "combined_all_passed": comb,
                "soft_passed": bool(gates.get("soft_passed")) if isinstance(gates, dict) else None,
                "promotion_recommendation": gates.get("promotion_recommendation") if isinstance(gates, dict) else None,
                "lens_mean_test_accuracy": _gate_mean(gates, track="per_date_lens", gate_id="lens_wf_mean_test_accuracy"),
                "instrument_mean_test_accuracy": _gate_mean(
                    gates, track="instrument_combo", gate_id="instrument_wf_mean_test_accuracy"
                ),
            }
            rows.append(row)

        best = None
        best_key = (-1.0, -1.0)
        for r in rows:
            lm = r.get("lens_mean_test_accuracy")
            im = r.get("instrument_mean_test_accuracy")
            if isinstance(lm, (int, float)) and isinstance(im, (int, float)):
                key = (float(lm), float(im))
                if key > best_key:
                    best_key = key
                    best = r.get("neutral_bps")

        sweep_doc = {
            "schema": "prophecy_btrack_recommended_nbps_sweep_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "inputs": {
                "neutral_bps_grid": grid,
                "sweep_dir": str(args.sweep_dir.resolve()),
                "recent_trading_days": int(args.recent_trading_days),
                "n_folds": int(args.n_folds),
                "hypothesis_json": str(args.hypothesis_json),
                "btc_csv": str(args.btc_csv),
            },
            "rows": rows,
            "best_neutral_bps_by_lens_then_instrument_mean": best,
            "any_combined_all_passed": any_strict,
        }
        args.sweep_summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.sweep_summary_json.write_text(json.dumps(sweep_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.sweep_summary_json.resolve()}")

        if args.sweep_promote_best_to_latest and first_promote_nb is not None:
            promote_paths = _ChainPaths(
                score_json=args.score_json,
                lens_out=args.lens_walkforward_out,
                inst_out=args.instrument_walkforward_out,
                gates_out=args.gates_out,
                streak_json=args.streak_history_json,
            )
            note = (
                f"recommended_chain_v1 promoted from sweep neutral_bps={first_promote_nb}; "
                "dual-leg + mild_downside + neutral_bps CLI."
            )
            prc, pr_steps, pr_gates = _run_one_recommended_eval(
                neutral_bps=float(first_promote_nb),
                paths=promote_paths,
                recent_trading_days=int(args.recent_trading_days),
                n_folds=int(args.n_folds),
                hypothesis_json=args.hypothesis_json,
                btc_csv=args.btc_csv,
                no_mild_downside=bool(args.no_mild_downside),
                skip_gates=bool(args.skip_gates),
                fail_on_gate=bool(args.fail_on_gate),
                calibration_note=note,
            )
            _write_summary(args.summary_out, pr_steps, gates=pr_gates, neutral_bps=float(first_promote_nb))
            return prc

        if args.apply_best_sweep_row_to_latest or auto_apply_after_sweep:
            return apply_best_sweep_row_to_latest(
                sweep_summary_json=args.sweep_summary_json,
                sweep_dir_fallback=args.sweep_dir,
                score_json=args.score_json,
                lens_out=args.lens_walkforward_out,
                inst_out=args.instrument_walkforward_out,
                gates_out=args.gates_out,
                summary_out=args.summary_out,
                hypothesis_json=args.hypothesis_json,
                streak_history_json=args.streak_history_json,
            )

        worst_rc = max((int(r.get("exit_code") or 0) for r in rows), default=0)
        return worst_rc

    calibration_note = str(args.calibration_note or "").strip() or (
        "recommended_chain_v1: reports-only artifacts; dual-leg + mild_downside + neutral_bps CLI."
    )
    paths = _ChainPaths(
        score_json=args.score_json,
        lens_out=args.lens_walkforward_out,
        inst_out=args.instrument_walkforward_out,
        gates_out=args.gates_out,
        streak_json=args.streak_history_json,
    )
    rc, steps, gates_payload = _run_one_recommended_eval(
        neutral_bps=float(args.neutral_bps),
        paths=paths,
        recent_trading_days=int(args.recent_trading_days),
        n_folds=int(args.n_folds),
        hypothesis_json=args.hypothesis_json,
        btc_csv=args.btc_csv,
        no_mild_downside=bool(args.no_mild_downside),
        skip_gates=bool(args.skip_gates),
        fail_on_gate=bool(args.fail_on_gate),
        calibration_note=calibration_note,
        per_date_direction_json=args.per_date_direction_json,
        include_source_direction_signal=bool(args.include_source_direction_signal),
        include_expanded_prior_features=bool(args.include_expanded_prior_features),
    )
    if rc != 0:
        _write_summary(args.summary_out, steps, gates=None, neutral_bps=float(args.neutral_bps))
        return rc
    if args.skip_gates:
        _write_summary(args.summary_out, steps, gates=None, neutral_bps=float(args.neutral_bps))
        return 0

    _write_summary(args.summary_out, steps, gates=gates_payload, neutral_bps=float(args.neutral_bps))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
