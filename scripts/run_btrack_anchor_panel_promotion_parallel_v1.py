#!/usr/bin/env python3
"""[HYPO] Parallel promotion gates (lens WF + btc_only) on anchor-30d score lanes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "reports/btrack_anchor_promotion_work"
OUT = ROOT / "reports/btrack_anchor_panel_promotion_parallel_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"

LANES: list[dict[str, str]] = [
    {
        "lane_id": "frozen_kpi_a",
        "score_json": "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json",
        "hit_eval_json": "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json",
    },
    {
        "lane_id": "v1_per_date",
        "score_json": "reports/btrack_prophecy_score_v1_prod_perdate_30d_v1.json",
        "hit_eval_json": "reports/prophecy_hit_rate_eval_v1_prod_perdate_30d_v1.json",
    },
    {
        "lane_id": "hybrid_ms_when_active_else_v1",
        "score_json": "reports/btrack_v1_ms_hybrid_work/ms_when_active_else_v1/score.json",
        "hit_eval_json": "reports/btrack_v1_ms_hybrid_work/ms_when_active_else_v1/eval.json",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _gate_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        "present": True,
        "combined_all_passed": doc.get("combined_all_passed"),
        "strict_passed": doc.get("strict_passed"),
        "soft_passed": doc.get("soft_passed"),
        "auto_promote_ready": doc.get("auto_promote_ready"),
        "promotion_recommendation": doc.get("promotion_recommendation"),
        "outcome_class": (doc.get("gate_taxonomy") or {}).get("outcome_class")
        if isinstance(doc.get("gate_taxonomy"), dict)
        else doc.get("outcome_class"),
    }


def _readiness(gates_path: Path, hit_path: Path, out_path: Path, py: str) -> dict[str, Any]:
    if not gates_path.is_file():
        return {"written": False}
    _run(
        [
            py,
            "scripts/build_prophecy_promotion_readiness_report_v1.py",
            "--gates-json",
            _rel(gates_path),
            "--hit-rate-json",
            _rel(hit_path),
            "--output",
            _rel(out_path),
        ]
    )
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    return {
        "written": True,
        "path": _rel(out_path),
        "auto_promote_ready": doc.get("auto_promote_ready"),
        "blockers": doc.get("blockers"),
    }


def _process_lane(lane: dict[str, str], *, py: str, n_folds: int) -> dict[str, Any]:
    lane_id = lane["lane_id"]
    score = ROOT / lane["score_json"]
    hit_eval = ROOT / lane["hit_eval_json"]
    if not score.is_file():
        return {"lane_id": lane_id, "error": f"missing_score:{score}"}

    lane_dir = WORK / lane_id
    lane_dir.mkdir(parents=True, exist_ok=True)
    wf_out = lane_dir / "lens_walkforward.json"
    gates_out = lane_dir / "promotion_gates.json"
    streak_out = lane_dir / "strict_streak.json"
    readiness_out = lane_dir / "readiness_report.json"

    _run(
        [
            py,
            "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
            "--score-json",
            _rel(score),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--target-instrument",
            "btc",
            "--n-folds",
            str(n_folds),
            "--include-source-direction-signal",
            "--include-expanded-prior-features",
            "--output",
            _rel(wf_out),
        ]
    )

    _run(
        [
            py,
            "scripts/eval_prophecy_promotion_gates_v1.py",
            "--lens-walkforward-json",
            _rel(wf_out),
            "--score-json",
            _rel(score),
            "--hypothesis-json",
            _rel(HYPO),
            "--promotion-track-mode",
            "btc_only_crossassist",
            "--skip-shared-gates",
            "--streak-history-json",
            _rel(streak_out),
            "--output",
            _rel(gates_out),
        ]
    )

    readiness = _readiness(gates_out, hit_eval, readiness_out, py)
    wf = json.loads(wf_out.read_text(encoding="utf-8")) if wf_out.is_file() else {}
    agg = wf.get("aggregate") or {}

    return {
        "lane_id": lane_id,
        "score_json": _rel(score),
        "walkforward": {
            "path": _rel(wf_out),
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
            "n_folds_effective": wf.get("n_folds_effective"),
        },
        "promotion_gates": {**_gate_summary(gates_out), "path": _rel(gates_out)},
        "readiness": readiness,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=3)
    ap.add_argument("--n-folds", type=int, default=4, help="Blocked WF folds for 30-day panel.")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    lanes_out: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = {
            pool.submit(_process_lane, lane, py=py, n_folds=args.n_folds): lane["lane_id"]
            for lane in LANES
        }
        for fut in as_completed(futures):
            lanes_out.append(fut.result())

    lanes_out.sort(key=lambda x: str(x.get("lane_id") or ""))
    passed = [
        l
        for l in lanes_out
        if (l.get("promotion_gates") or {}).get("combined_all_passed")
    ]

    pack = {
        "schema": "btrack_anchor_panel_promotion_parallel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": "anchor_30d_btc",
        "mode": "btc_only_crossassist_skip_shared_gates",
        "n_folds": args.n_folds,
        "lanes": lanes_out,
        "lanes_combined_pass_count": len(passed),
        "lanes_combined_pass_ids": [l.get("lane_id") for l in passed],
        "operator_lines": [
            "- [MKM-ANCHOR-GATES] WF+gates on frozen/v1/hybrid anchor scores only; prod *_latest untouched.",
            "- [MKM-ANCHOR-GATES] combined_all_passed does not auto-promote Track A or live trading.",
            "- [MKM-ANCHOR-GATES] Compare with hit-rate snapshot before human review.",
        ],
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"combined_pass: {len(passed)}/{len(lanes_out)} {pack['lanes_combined_pass_ids']}")
    err = [l for l in lanes_out if l.get("error")]
    if err:
        print(f"errors: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
