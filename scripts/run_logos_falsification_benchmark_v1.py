#!/usr/bin/env python3
"""Run falsification benchmark plan for Logos-vs-controls (research only)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_benchmark_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


def _build_arm(
    arm_id: str,
    family: str,
    symbol_map: str,
    news_jsonl: str,
    labels_jsonl: str,
    out_suffix: str,
) -> dict[str, Any]:
    return {
        "arm_id": arm_id,
        "theory_family": family,
        "status": "available",
        "run_cmd": [
            "py",
            "scripts/run_logos_symbolic_event_backtest_v1.py",
            "--news-jsonl",
            news_jsonl,
            "--labels-jsonl",
            labels_jsonl,
            "--symbol-map-json",
            symbol_map,
            "--output-json",
            f"docs/final/artifacts/logos_symbolic_event_backtest_benchmark_{out_suffix}_latest.json",
            "--output-csv",
            f"docs/final/artifacts/logos_symbolic_event_backtest_benchmark_{out_suffix}_rows_latest.csv",
        ],
        "result_json": f"docs/final/artifacts/logos_symbolic_event_backtest_benchmark_{out_suffix}_latest.json",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Falsification benchmark for Logos against controls.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--execute", action="store_true", help="Run available benchmark arms.")
    ap.add_argument(
        "--holdout-news-jsonl",
        default="tests/fixtures/logos_symbolic_event_backtest_news_holdout_v1.jsonl",
    )
    ap.add_argument(
        "--holdout-labels-jsonl",
        default="tests/fixtures/logos_symbolic_event_backtest_labels_holdout_v1.jsonl",
    )
    ap.add_argument(
        "--real-news-jsonl",
        default="docs/final/artifacts/news_observation_v1_blind_split_latest.jsonl",
    )
    ap.add_argument(
        "--real-labels-jsonl",
        default="docs/final/artifacts/direction_label_bar_v1_latest.jsonl",
    )
    ap.add_argument(
        "--include-real-oos",
        action="store_true",
        help="Also run OOS arms on real artifact JSONL paths when files exist.",
    )
    args = ap.parse_args()

    base_news = "tests/fixtures/logos_symbolic_event_backtest_news_smoke_v1.jsonl"
    base_labels = "tests/fixtures/logos_symbolic_event_backtest_labels_smoke_v1.jsonl"
    holdout_news = str(args.holdout_news_jsonl)
    holdout_labels = str(args.holdout_labels_jsonl)
    real_news = str(args.real_news_jsonl)
    real_labels = str(args.real_labels_jsonl)

    in_sample_arms: list[dict[str, Any]] = [
        _build_arm("logos_primary", "logos", "docs/final/artifacts/logos_symbolic_event_map_v1.json", base_news, base_labels, "logos"),
        _build_arm("counterfactual_variant_v1", "counterfactual", "docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json", base_news, base_labels, "counterfactual"),
        _build_arm("dummy_negative_control", "dummy_control", "docs/final/artifacts/logos_symbolic_event_map_dummy_v1.json", base_news, base_labels, "dummy"),
        _build_arm("iching_adapter_v1", "iching", "docs/final/artifacts/logos_symbolic_event_map_iching_v1.json", base_news, base_labels, "iching"),
        _build_arm("quantum_adapter_v1", "quantum_inspired", "docs/final/artifacts/logos_symbolic_event_map_quantum_v1.json", base_news, base_labels, "quantum"),
    ]
    holdout_arms: list[dict[str, Any]] = [
        _build_arm("logos_primary_oos", "logos", "docs/final/artifacts/logos_symbolic_event_map_v1.json", holdout_news, holdout_labels, "logos_oos"),
        _build_arm("counterfactual_variant_v1_oos", "counterfactual", "docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json", holdout_news, holdout_labels, "counterfactual_oos"),
        _build_arm("dummy_negative_control_oos", "dummy_control", "docs/final/artifacts/logos_symbolic_event_map_dummy_v1.json", holdout_news, holdout_labels, "dummy_oos"),
        _build_arm("iching_adapter_v1_oos", "iching", "docs/final/artifacts/logos_symbolic_event_map_iching_v1.json", holdout_news, holdout_labels, "iching_oos"),
        _build_arm("quantum_adapter_v1_oos", "quantum_inspired", "docs/final/artifacts/logos_symbolic_event_map_quantum_v1.json", holdout_news, holdout_labels, "quantum_oos"),
    ]
    real_arms: list[dict[str, Any]] = []
    if args.include_real_oos:
        real_news_path = ROOT / real_news
        real_labels_path = ROOT / real_labels
        if real_news_path.is_file() and real_labels_path.is_file():
            real_arms = [
                _build_arm("logos_primary_real_oos", "logos", "docs/final/artifacts/logos_symbolic_event_map_v1.json", real_news, real_labels, "logos_real_oos"),
                _build_arm("counterfactual_variant_v1_real_oos", "counterfactual", "docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json", real_news, real_labels, "counterfactual_real_oos"),
                _build_arm("dummy_negative_control_real_oos", "dummy_control", "docs/final/artifacts/logos_symbolic_event_map_dummy_v1.json", real_news, real_labels, "dummy_real_oos"),
                _build_arm("iching_adapter_v1_real_oos", "iching", "docs/final/artifacts/logos_symbolic_event_map_iching_v1.json", real_news, real_labels, "iching_real_oos"),
                _build_arm("quantum_adapter_v1_real_oos", "quantum_inspired", "docs/final/artifacts/logos_symbolic_event_map_quantum_v1.json", real_news, real_labels, "quantum_real_oos"),
            ]
    arms: list[dict[str, Any]] = [*in_sample_arms, *holdout_arms, *real_arms]

    run_log: list[dict[str, Any]] = []
    if args.execute:
        for arm in arms:
            if arm.get("status") != "available":
                continue
            cmd = arm.get("run_cmd")
            if not isinstance(cmd, list):
                continue
            rc, out, err = _run([str(x) for x in cmd], ROOT)
            run_log.append(
                {
                    "arm_id": arm["arm_id"],
                    "return_code": rc,
                    "stdout_tail": out[-1200:],
                    "stderr_tail": err[-1200:],
                }
            )

    metrics: dict[str, Any] = {}
    for arm in arms:
        result_json = arm.get("result_json")
        if not isinstance(result_json, str):
            continue
        p = ROOT / result_json
        if not p.is_file():
            continue
        doc = _load_json(p)
        summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
        metrics[arm["arm_id"]] = {
            "hit_rate": summary.get("hit_rate"),
            "n_evaluated": summary.get("n_evaluated"),
            "hits": summary.get("hits"),
        }

    logos_rate = metrics.get("logos_primary", {}).get("hit_rate")
    cf_rate = metrics.get("counterfactual_variant_v1", {}).get("hit_rate")
    dummy_rate = metrics.get("dummy_negative_control", {}).get("hit_rate")
    iching_rate = metrics.get("iching_adapter_v1", {}).get("hit_rate")
    quantum_rate = metrics.get("quantum_adapter_v1", {}).get("hit_rate")
    logos_oos_rate = metrics.get("logos_primary_oos", {}).get("hit_rate")
    cf_oos_rate = metrics.get("counterfactual_variant_v1_oos", {}).get("hit_rate")
    dummy_oos_rate = metrics.get("dummy_negative_control_oos", {}).get("hit_rate")
    iching_oos_rate = metrics.get("iching_adapter_v1_oos", {}).get("hit_rate")
    quantum_oos_rate = metrics.get("quantum_adapter_v1_oos", {}).get("hit_rate")
    logos_real_oos_rate = metrics.get("logos_primary_real_oos", {}).get("hit_rate")
    cf_real_oos_rate = metrics.get("counterfactual_variant_v1_real_oos", {}).get("hit_rate")
    dummy_real_oos_rate = metrics.get("dummy_negative_control_real_oos", {}).get("hit_rate")
    iching_real_oos_rate = metrics.get("iching_adapter_v1_real_oos", {}).get("hit_rate")
    quantum_real_oos_rate = metrics.get("quantum_adapter_v1_real_oos", {}).get("hit_rate")
    uplift_over_dummy = None
    uplift_over_counterfactual = None
    uplift_over_iching = None
    uplift_over_quantum = None
    if isinstance(logos_rate, (float, int)) and isinstance(dummy_rate, (float, int)):
        uplift_over_dummy = round(float(logos_rate) - float(dummy_rate), 6)
    if isinstance(logos_rate, (float, int)) and isinstance(cf_rate, (float, int)):
        uplift_over_counterfactual = round(float(logos_rate) - float(cf_rate), 6)
    if isinstance(logos_rate, (float, int)) and isinstance(iching_rate, (float, int)):
        uplift_over_iching = round(float(logos_rate) - float(iching_rate), 6)
    if isinstance(logos_rate, (float, int)) and isinstance(quantum_rate, (float, int)):
        uplift_over_quantum = round(float(logos_rate) - float(quantum_rate), 6)
    uplift_oos_over_dummy = None
    uplift_oos_over_counterfactual = None
    uplift_oos_over_iching = None
    uplift_oos_over_quantum = None
    if isinstance(logos_oos_rate, (float, int)) and isinstance(dummy_oos_rate, (float, int)):
        uplift_oos_over_dummy = round(float(logos_oos_rate) - float(dummy_oos_rate), 6)
    if isinstance(logos_oos_rate, (float, int)) and isinstance(cf_oos_rate, (float, int)):
        uplift_oos_over_counterfactual = round(float(logos_oos_rate) - float(cf_oos_rate), 6)
    if isinstance(logos_oos_rate, (float, int)) and isinstance(iching_oos_rate, (float, int)):
        uplift_oos_over_iching = round(float(logos_oos_rate) - float(iching_oos_rate), 6)
    if isinstance(logos_oos_rate, (float, int)) and isinstance(quantum_oos_rate, (float, int)):
        uplift_oos_over_quantum = round(float(logos_oos_rate) - float(quantum_oos_rate), 6)
    uplift_real_oos_over_dummy = None
    uplift_real_oos_over_counterfactual = None
    uplift_real_oos_over_iching = None
    uplift_real_oos_over_quantum = None
    if isinstance(logos_real_oos_rate, (float, int)) and isinstance(dummy_real_oos_rate, (float, int)):
        uplift_real_oos_over_dummy = round(float(logos_real_oos_rate) - float(dummy_real_oos_rate), 6)
    if isinstance(logos_real_oos_rate, (float, int)) and isinstance(cf_real_oos_rate, (float, int)):
        uplift_real_oos_over_counterfactual = round(float(logos_real_oos_rate) - float(cf_real_oos_rate), 6)
    if isinstance(logos_real_oos_rate, (float, int)) and isinstance(iching_real_oos_rate, (float, int)):
        uplift_real_oos_over_iching = round(float(logos_real_oos_rate) - float(iching_real_oos_rate), 6)
    if isinstance(logos_real_oos_rate, (float, int)) and isinstance(quantum_real_oos_rate, (float, int)):
        uplift_real_oos_over_quantum = round(float(logos_real_oos_rate) - float(quantum_real_oos_rate), 6)

    negative_control_pass = isinstance(uplift_oos_over_dummy, float) and uplift_oos_over_dummy > 0.0
    counterfactual_pass = isinstance(uplift_oos_over_counterfactual, float) and uplift_oos_over_counterfactual > 0.0
    out_of_sample_pass = isinstance(logos_oos_rate, (float, int))
    real_out_of_sample_pass = (
        (not args.include_real_oos)
        or (
            isinstance(logos_real_oos_rate, (float, int))
            and isinstance(uplift_real_oos_over_dummy, float)
            and uplift_real_oos_over_dummy > 0.0
            and isinstance(uplift_real_oos_over_counterfactual, float)
            and uplift_real_oos_over_counterfactual > 0.0
            and isinstance(uplift_real_oos_over_quantum, float)
            and uplift_real_oos_over_quantum > 0.0
        )
    )
    three_gate_pass = bool(
        negative_control_pass
        and counterfactual_pass
        and out_of_sample_pass
        and real_out_of_sample_pass
    )

    payload = {
        "schema": "logos_falsification_benchmark_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "fact_lock_notice": "Do not claim cross-theory superiority unless all required adapters and OOS gates are present.",
        "required_gates": [
            "negative_control_uplift",
            "counterfactual_gap",
            "out_of_sample_holdout",
        ],
        "arms": arms,
        "metrics": metrics,
        "uplift_over_dummy": uplift_over_dummy,
        "uplift_over_counterfactual": uplift_over_counterfactual,
        "uplift_over_iching": uplift_over_iching,
        "uplift_over_quantum": uplift_over_quantum,
        "uplift_oos_over_dummy": uplift_oos_over_dummy,
        "uplift_oos_over_counterfactual": uplift_oos_over_counterfactual,
        "uplift_oos_over_iching": uplift_oos_over_iching,
        "uplift_oos_over_quantum": uplift_oos_over_quantum,
        "uplift_real_oos_over_dummy": uplift_real_oos_over_dummy,
        "uplift_real_oos_over_counterfactual": uplift_real_oos_over_counterfactual,
        "uplift_real_oos_over_iching": uplift_real_oos_over_iching,
        "uplift_real_oos_over_quantum": uplift_real_oos_over_quantum,
        "gate_status": {
            "negative_control_uplift": "PASS" if negative_control_pass else "FAIL",
            "counterfactual_gap": "PASS" if counterfactual_pass else "FAIL",
            "out_of_sample_holdout": "PASS" if out_of_sample_pass else "FAIL",
            "real_out_of_sample_holdout": "PASS" if real_out_of_sample_pass else "FAIL",
            "three_gate_overall": "PASS" if three_gate_pass else "FAIL",
        },
        "execution_mode": "execute" if args.execute else "dry_run",
        "run_log": run_log,
        "next_actions": [
            "Add OOS holdout and walk-forward gate for all arms.",
            "Expand from smoke fixtures to production holdout dataset before any superiority claim.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.execute:
        _run(
            [
                "py",
                "scripts/build_logos_falsification_walkforward_v1.py",
                "--benchmark-json",
                str(args.output_json),
                "--output-json",
                "docs/final/artifacts/logos_falsification_walkforward_latest.json",
            ],
            ROOT,
        )
        if args.include_real_oos:
            _run(
                [
                    "py",
                    "scripts/build_logos_falsification_contrastive_slice_v1.py",
                    "--output-json",
                    "docs/final/artifacts/logos_falsification_contrastive_slice_latest.json",
                ],
                ROOT,
            )
    print(json.dumps({"ok": True, "output": str(args.output_json), "mode": payload["execution_mode"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
