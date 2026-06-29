#!/usr/bin/env python3
"""[HYPO] Baseline lens WF ablation — no expanded-prior (promotion-legal axis)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LENS_WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"
BUILD = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
GATES = ROOT / "scripts/eval_prophecy_promotion_gates_v1.py"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_180d_v1_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_dual_leading_180d_v1.json"
INST_BEST = ROOT / "reports/_instrument_wf_bottleneck_work/inst_wf_nf6_beat_bull_first_inner-cv_ensemble-top3.json"
DEFAULT_OUT = ROOT / "reports/baseline_lens_wf_ablation_v1_latest.json"
WORK = ROOT / "reports/_baseline_lens_wf_ablation_work"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
STREAK = ROOT / "reports/prophecy_promotion_strict_streak_recommended_chain_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_rc(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True).returncode


def _mean_from_wf(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    mean = agg.get("mean_test_accuracy")
    return {
        "mean_test_accuracy": mean,
        "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
        "min_test_accuracy": agg.get("min_test_accuracy"),
        "fraction_test_beats_always_bull": agg.get("fraction_test_beats_always_bull"),
        "gate_055_pass": isinstance(mean, (int, float)) and float(mean) >= 0.55,
    }


def _ensure_score_nbps(*, nbps: float, dual: Path) -> Path:
    out = WORK / f"score_nbps_{str(nbps).replace('.', '_')}.json"
    if out.is_file():
        return out
    rc = _run_rc(
        [
            sys.executable,
            str(BUILD),
            "--force-dual-leg-panel",
            "--per-date-direction-json",
            str(dual),
            "--btc-csv",
            str(BTC),
            "--kospi-csv",
            str(KOSPI),
            "--recent-trading-days",
            "180",
            "--neutral-bps",
            str(nbps),
            "--output",
            str(out),
        ]
    )
    if rc != 0:
        raise RuntimeError(f"score rebuild nbps={nbps} rc={rc}")
    return out


def _combined_pass(lens_wf: Path, score: Path) -> bool | None:
    if not INST_BEST.is_file():
        return None
    gates_out = WORK / f"gates_{lens_wf.stem}.json"
    rc = _run_rc(
        [
            sys.executable,
            str(GATES),
            "--promotion-track-mode",
            "dual",
            "--lens-walkforward-json",
            str(lens_wf),
            "--instrument-walkforward-json",
            str(INST_BEST),
            "--score-json",
            str(score),
            "--hypothesis-json",
            str(HYPO),
            "--streak-history-json",
            str(STREAK),
            "--output",
            str(gates_out),
            "--calibration-note",
            "baseline_lens_ablation no expanded prior",
        ]
    )
    if rc != 0 or not gates_out.is_file():
        return None
    g = json.loads(gates_out.read_text(encoding="utf-8-sig"))
    return bool(g.get("combined_all_passed"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--include-nbps-rebuild", action="store_true")
    ap.add_argument("--pair-combined-gates", action="store_true", help="Run combined gates for lens>=0.55 variants.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    dual = args.dual_json if args.dual_json.is_absolute() else ROOT / args.dual_json
    WORK.mkdir(parents=True, exist_ok=True)

    specs: list[dict[str, Any]] = []
    for n_folds in (4, 5, 6, 7):
        for obj in ("margin_vs_bull", "accuracy"):
            for src in (False, True):
                specs.append(
                    {
                        "n_folds": n_folds,
                        "train_objective": obj,
                        "include_source_direction_signal": src,
                        "extra_args": [],
                    }
                )
    for tag, extra in [
        ("regime_adaptive", ["--regime-adaptive-bull-train", "--regime-adaptive-lookback-days", "60"]),
        ("regime_contrarian", ["--regime-adaptive-bull-train", "--regime-adaptive-lookback-days", "60", "--regime-adaptive-contrarian-guard"]),
        ("min_w_cross_0", ["--train-min-w-cross", "0"]),
        ("regime_min_w_cross", ["--regime-adaptive-min-w-cross", "--regime-bull-train-floor", "0.52"]),
    ]:
        specs.append(
            {
                "n_folds": 6,
                "train_objective": "margin_vs_bull",
                "include_source_direction_signal": False,
                "extra_args": extra,
                "tag": tag,
            }
        )

    rows: list[dict[str, Any]] = []
    scores_to_run: list[tuple[float | None, Path]] = []
    if score.is_file():
        scores_to_run.append((None, score))
    if args.include_nbps_rebuild and dual.is_file():
        for nbps in (1.5, 2.0, 3.0, 4.0):
            try:
                scores_to_run.append((nbps, _ensure_score_nbps(nbps=nbps, dual=dual)))
            except RuntimeError as exc:
                rows.append({"error": str(exc), "neutral_bps": nbps})

    for nbps, sc in scores_to_run:
        for spec in specs:
            tag = spec.get("tag") or ""
            src = "srcdir" if spec["include_source_direction_signal"] else "nosrc"
            slug = f"nf{spec['n_folds']}_{spec['train_objective']}_{src}"
            if tag:
                slug += f"_{tag}"
            if nbps is not None:
                slug += f"_nbps{str(nbps).replace('.', '_')}"
            out = WORK / f"lens_wf_{slug}.json"
            cmd = [
                sys.executable,
                str(LENS_WF),
                "--score-json",
                str(sc),
                "--btc-csv",
                str(BTC),
                "--kospi-csv",
                str(KOSPI),
                "--target-instrument",
                "btc",
                "--train-objective",
                spec["train_objective"],
                "--n-folds",
                str(spec["n_folds"]),
                "--output",
                str(out),
            ]
            if spec["include_source_direction_signal"]:
                cmd.append("--include-source-direction-signal")
            cmd.extend(spec.get("extra_args") or [])
            rc = _run_rc(cmd)
            row: dict[str, Any] = {**spec, "slug": slug, "exit_code": rc, "score_json": str(sc)}
            if nbps is not None:
                row["neutral_bps"] = nbps
            if rc == 0 and out.is_file():
                row.update(_mean_from_wf(out))
                row["walkforward_json"] = str(out.relative_to(ROOT)).replace("\\", "/")
                if args.pair_combined_gates and row.get("gate_055_pass"):
                    row["combined_all_passed_with_inst_ensemble_nf6"] = _combined_pass(out, sc)
            rows.append(row)
            print(f"{slug}: mean={row.get('mean_test_accuracy')} pass055={row.get('gate_055_pass')} combined={row.get('combined_all_passed_with_inst_ensemble_nf6')}")

    passing = [r for r in rows if r.get("gate_055_pass")]
    best = max(
        (r for r in rows if isinstance(r.get("mean_test_accuracy"), (int, float))),
        key=lambda x: float(x["mean_test_accuracy"]),
        default=None,
    )
    combined_passers = [r for r in rows if r.get("combined_all_passed_with_inst_ensemble_nf6")]

    doc = {
        "schema": "baseline_lens_wf_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "expanded_prior_excluded": True,
        "promotion_axis_note": "Only non-expanded-prior lens variants — eligible for promotion-axis research (human sign-off still required).",
        "variants_n": len(rows),
        "variants": rows,
        "best_by_mean_test_accuracy": best,
        "gate_055_pass_count": len(passing),
        "combined_pass_with_inst_ensemble_nf6": combined_passers,
        "any_combined_all_passed_no_expanded_prior": bool(combined_passers),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} pass055={len(passing)} combined={len(combined_passers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
