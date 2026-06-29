#!/usr/bin/env python3
"""[HYPO] Ambiguous-score conditional micro-oscillator ablation (frozen KOSPI lens WF)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "prophecy_micro_oscillator_ambiguous_ablation_v1_latest.json"
WF = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"id": "baseline_no_micro", "args": ["--micro-oscillator-mode", "off"]},
    {
        "id": "mom_ret1_ambiguous",
        "args": [
            "--micro-oscillator-mode",
            "mom_ret1",
            "--micro-oscillator-trigger",
            "ambiguous",
        ],
    },
    {
        "id": "mom_ret1_ambiguous_m015",
        "args": [
            "--micro-oscillator-mode",
            "mom_ret1",
            "--micro-oscillator-trigger",
            "ambiguous",
            "--micro-oscillator-ambiguous-margin",
            "0.15",
        ],
    },
    {
        "id": "mom_ret1_ambiguous_m025",
        "args": [
            "--micro-oscillator-mode",
            "mom_ret1",
            "--micro-oscillator-trigger",
            "ambiguous",
            "--micro-oscillator-ambiguous-margin",
            "0.25",
        ],
    },
    {
        "id": "revert_ret1_ambiguous",
        "args": [
            "--micro-oscillator-mode",
            "revert_ret1",
            "--micro-oscillator-trigger",
            "ambiguous",
        ],
    },
    {
        "id": "composite_ret1_ret3_ambiguous",
        "args": [
            "--micro-oscillator-mode",
            "composite_ret1_ret3",
            "--micro-oscillator-trigger",
            "ambiguous",
        ],
    },
    {
        "id": "mom_ret3_ambiguous",
        "args": [
            "--micro-oscillator-mode",
            "mom_ret3",
            "--micro-oscillator-trigger",
            "ambiguous",
        ],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_variant(
    *,
    score_json: Path,
    n_folds: int,
    variant_id: str,
    extra_args: list[str],
    tmp_dir: Path,
) -> dict[str, Any]:
    out = tmp_dir / f"wf_amb_{variant_id}.json"
    cmd = [
        sys.executable,
        str(WF),
        "--score-json",
        str(score_json),
        "--target-instrument",
        "kospi",
        "--grid-profile",
        "kospi_bear_extended",
        "--train-objective",
        "beat_bull_first",
        "--regime-adaptive-lens-features",
        "--regime-expanded-features-bull-min",
        "0.60",
        "--regime-expanded-features-bull-max",
        "0.625",
        "--n-folds",
        str(n_folds),
        "--output",
        str(out),
    ]
    cmd.extend(extra_args)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    row: dict[str, Any] = {
        "variant_id": variant_id,
        "exit_code": int(proc.returncode),
        "walkforward_json": str(out),
    }
    if proc.returncode != 0:
        row["stderr_tail"] = (proc.stderr or "")[-2000:]
        return row
    if not out.is_file():
        row["error"] = "missing_output"
        return row
    doc = json.loads(out.read_text(encoding="utf-8"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    inputs = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
    folds = doc.get("folds") if isinstance(doc.get("folds"), list) else []
    micro_applied_total = sum(
        int((f or {}).get("micro_oscillator_applied_count") or 0) for f in folds if isinstance(f, dict)
    )
    row.update(
        {
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "fraction_test_beats_always_bull_gt": agg.get("fraction_test_beats_always_bull"),
            "fraction_test_meets_or_beats_always_bull_gte": agg.get("fraction_test_meets_or_beats_always_bull"),
            "micro_oscillator_mode": inputs.get("micro_oscillator_mode"),
            "micro_oscillator_trigger": inputs.get("micro_oscillator_trigger"),
            "micro_oscillator_ambiguous_margin": inputs.get("micro_oscillator_ambiguous_margin"),
            "micro_oscillator_applied_total": micro_applied_total,
        }
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="Ambiguous-score micro-oscillator ablation.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--tmp-dir", type=Path, default=ROOT / "reports" / "tmp_micro_oscillator_ambiguous_ablation")
    args = ap.parse_args()

    if not args.score_json.is_file():
        print(f"Missing: {args.score_json}", flush=True)
        return 2

    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        _run_variant(
            score_json=args.score_json,
            n_folds=int(args.n_folds),
            variant_id=str(v["id"]),
            extra_args=list(v.get("args") or []),
            tmp_dir=args.tmp_dir,
        )
        for v in VARIANTS
    ]

    def _exit_ok(r: dict[str, Any]) -> bool:
        ec = r.get("exit_code")
        return ec is not None and int(ec) == 0

    ok_rows = [r for r in rows if _exit_ok(r)]
    failed = [r for r in rows if not _exit_ok(r)]
    baseline = next((r for r in ok_rows if r.get("variant_id") == "baseline_no_micro"), None)

    def _rank_gt(r: dict[str, Any]) -> tuple[float, float, float]:
        return (
            float(r.get("fraction_test_beats_always_bull_gt") or 0.0),
            float(r.get("mean_test_accuracy") or 0.0),
            float(r.get("micro_oscillator_applied_total") or 0.0),
        )

    best_gt = max(ok_rows, key=_rank_gt) if ok_rows else None
    payload: dict[str, Any] = {
        "schema": "prophecy_micro_oscillator_ambiguous_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json.resolve()),
            "n_folds": int(args.n_folds),
            "note": "Micro applies on test when combo score in (down_thr, up_thr) or within ambiguous margin.",
        },
        "variants": rows,
        "failed_variant_count": len(failed),
        "baseline": baseline,
        "best_by_gt_frac": best_gt,
        "verdict": None,
    }
    if baseline and best_gt:
        gt_lift = float(best_gt.get("fraction_test_beats_always_bull_gt") or 0.0) - float(
            baseline.get("fraction_test_beats_always_bull_gt") or 0.0
        )
        mean_delta = float(best_gt.get("mean_test_accuracy") or 0.0) - float(
            baseline.get("mean_test_accuracy") or 0.0
        )
        payload["verdict"] = {
            "gt_frac_lift_vs_baseline": round(gt_lift, 6),
            "mean_delta_best_gt_vs_baseline": round(mean_delta, 6),
            "promote_micro_layer": bool(gt_lift > 0.0 and mean_delta >= 0.0),
            "best_variant_id": best_gt.get("variant_id"),
            "micro_applied_total": best_gt.get("micro_oscillator_applied_total"),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}", flush=True)
    if payload.get("verdict"):
        print(f"verdict={payload['verdict']}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
