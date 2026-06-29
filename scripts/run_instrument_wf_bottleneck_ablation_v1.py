#!/usr/bin/env python3
"""[HYPO] Instrument WF bottleneck ablation: n_folds x objective x selection x test_policy (+ optional nbps rebuild)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INST_WF = ROOT / "scripts/run_prophecy_instrument_combo_walkforward_v1.py"
BUILD = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_expanded_hypo_180d_v1_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_dual_leading_180d_v1.json"
DEFAULT_OUT = ROOT / "reports/instrument_wf_bottleneck_ablation_v1_latest.json"
WORK = ROOT / "reports/_instrument_wf_bottleneck_work"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_rc(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True).returncode


def _mean_from_wf(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    return {
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
        "min_test_accuracy": agg.get("min_test_accuracy"),
        "fraction_test_beats_always_bull": agg.get("fraction_test_beats_always_bull"),
        "gate_055_pass": isinstance(agg.get("mean_test_accuracy"), (int, float)) and float(agg["mean_test_accuracy"]) >= 0.55,
    }


def _ensure_score_for_nbps(
    *,
    nbps: float,
    dual_json: Path,
    work: Path,
) -> Path:
    out = work / f"score_nbps_{str(nbps).replace('.', '_')}.json"
    if out.is_file():
        return out
    cmd = [
        sys.executable,
        str(BUILD),
        "--force-dual-leg-panel",
        "--per-date-direction-json",
        str(dual_json),
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
    rc = _run_rc(cmd)
    if rc != 0 or not out.is_file():
        raise RuntimeError(f"score rebuild failed nbps={nbps} rc={rc}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--include-nbps-rebuild", action="store_true", help="Also sweep neutral_bps with score rebuild.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    dual = args.dual_json if args.dual_json.is_absolute() else ROOT / args.dual_json
    if not score.is_file():
        raise SystemExit(f"missing score: {score}")

    WORK.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict[str, Any]] = []

    grid: list[dict[str, Any]] = []
    for n_folds in (4, 5, 6, 7):
        for obj in ("beat_bull_first", "margin_vs_bull", "stability_margin"):
            for sel in ("inner-cv", "full-train"):
                for policy in ("single", "ensemble-top3"):
                    grid.append(
                        {
                            "n_folds": n_folds,
                            "train_objective": obj,
                            "selection_mode": sel,
                            "test_policy": policy,
                        }
                    )

    for spec in grid:
        slug = f"nf{spec['n_folds']}_{spec['train_objective']}_{spec['selection_mode']}_{spec['test_policy']}"
        out = WORK / f"inst_wf_{slug}.json"
        cmd = [
            sys.executable,
            str(INST_WF),
            "--score-json",
            str(score),
            "--btc-csv",
            str(BTC),
            "--kospi-csv",
            str(KOSPI),
            "--n-folds",
            str(spec["n_folds"]),
            "--train-objective",
            spec["train_objective"],
            "--selection-mode",
            spec["selection_mode"],
            "--test-policy",
            spec["test_policy"],
            "--inject-sweep-best",
            "--output",
            str(out),
        ]
        if spec["selection_mode"] == "inner-cv":
            cmd.extend(["--inner-folds", "3"])
        rc = _run_rc(cmd)
        row: dict[str, Any] = {**spec, "slug": slug, "exit_code": rc, "score_json": str(score)}
        if rc == 0 and out.is_file():
            row.update(_mean_from_wf(out))
            row["walkforward_json"] = str(out.relative_to(ROOT)).replace("\\", "/")
        rows_out.append(row)
        print(f"{slug}: mean={row.get('mean_test_accuracy')} pass055={row.get('gate_055_pass')}")

    if args.include_nbps_rebuild:
        if not dual.is_file():
            raise SystemExit(f"--include-nbps-rebuild requires dual-json: {dual}")
        for nbps in (1.5, 2.0, 3.0, 4.0, 6.0):
            try:
                nbps_score = _ensure_score_for_nbps(nbps=nbps, dual_json=dual, work=WORK)
            except RuntimeError as e:
                rows_out.append({"slug": f"nbps_{nbps}", "error": str(e)})
                continue
            slug = f"nbps_{str(nbps).replace('.', '_')}_nf6_chain_default"
            out = WORK / f"inst_wf_{slug}.json"
            cmd = [
                sys.executable,
                str(INST_WF),
                "--score-json",
                str(nbps_score),
                "--btc-csv",
                str(BTC),
                "--kospi-csv",
                str(KOSPI),
                "--n-folds",
                "6",
                "--train-objective",
                "beat_bull_first",
                "--selection-mode",
                "inner-cv",
                "--inner-folds",
                "3",
                "--inject-sweep-best",
                "--output",
                str(out),
            ]
            rc = _run_rc(cmd)
            row = {
                "slug": slug,
                "neutral_bps": nbps,
                "n_folds": 6,
                "train_objective": "beat_bull_first",
                "selection_mode": "inner-cv",
                "test_policy": "single",
                "exit_code": rc,
                "score_json": str(nbps_score.relative_to(ROOT)).replace("\\", "/"),
            }
            if rc == 0 and out.is_file():
                row.update(_mean_from_wf(out))
                row["walkforward_json"] = str(out.relative_to(ROOT)).replace("\\", "/")
            rows_out.append(row)
            print(f"{slug}: mean={row.get('mean_test_accuracy')} pass055={row.get('gate_055_pass')}")

    passing = [r for r in rows_out if r.get("gate_055_pass")]
    best = max(
        (r for r in rows_out if isinstance(r.get("mean_test_accuracy"), (int, float))),
        key=lambda x: float(x["mean_test_accuracy"]),
        default=None,
    )
    chain_default = next((r for r in rows_out if r.get("slug") == "nf6_beat_bull_first_inner-cv_single"), None)

    doc = {
        "schema": "instrument_wf_bottleneck_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "score_json": str(score.relative_to(ROOT)).replace("\\", "/") if score.is_relative_to(ROOT) else str(score),
        "variants_n": len(rows_out),
        "variants": rows_out,
        "chain_default_nf6_inner_cv": chain_default,
        "best_by_mean_test_accuracy": best,
        "any_gate_055_pass": bool(passing),
        "gate_055_pass_count": len(passing),
        "promotion_note": "Instrument WF pass alone does not imply combined_all_passed or Track A promotion.",
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} best={best.get('slug') if best else None} mean={best.get('mean_test_accuracy') if best else None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
