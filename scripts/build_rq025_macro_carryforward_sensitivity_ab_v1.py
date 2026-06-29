#!/usr/bin/env python3
"""[HYPO] A/B: vault-observed macro vs local carry-forward merged overlay — intersection WF."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_macro_carryforward_sensitivity_ab_v1_latest.json"
SCHEMA = "rq025_macro_carryforward_sensitivity_ab_v1"
WIDE_SCRIPT = ROOT / "scripts/build_rq025_flow_fred_wide_join_hypo_v1.py"
CAUSAL_SCRIPT = ROOT / "scripts/build_rq025_causal_feature_filter_poc_v1.py"
WF_SCRIPT = ROOT / "scripts/build_rq025_gbdt_shadow_hypo_v1.py"
MERGED_CSV = ROOT / "reports/rq025_sgp_history_merged_hypo_v1.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}")


def _arm_pipeline(
    arm_id: str,
    wide_out: Path,
    *,
    overlay: bool,
) -> dict[str, Any]:
    wide_cmd = [sys.executable, str(WIDE_SCRIPT), "--output", str(wide_out)]
    if overlay:
        wide_cmd.extend(
            ["--macro-csv", str(MERGED_CSV), "--macro-csv-overlay"]
        )
    _run(wide_cmd)
    wide = _load(wide_out)
    hy = (wide.get("cohorts") or {}).get("hybrid_kospi_252d") or {}

    causal_out = ROOT / f"reports/rq025_ab_{arm_id}_causal_hypo_v1_latest.json"
    wf_out = ROOT / f"reports/rq025_ab_{arm_id}_wf_hypo_v1_latest.json"
    _run(
        [
            sys.executable,
            str(CAUSAL_SCRIPT),
            "--wide-join-json",
            str(wide_out.relative_to(ROOT)).replace("\\", "/"),
            "--cohort",
            "hybrid_kospi_252d",
            "--feature-set",
            "all",
            "--profile",
            "hybrid_relaxed",
            "--require-intersection",
            "--output",
            str(causal_out),
        ]
    )
    causal = _load(causal_out)
    _run(
        [
            sys.executable,
            str(WF_SCRIPT),
            "--wide-join-json",
            str(wide_out.relative_to(ROOT)).replace("\\", "/"),
            "--causal-json",
            str(causal_out.relative_to(ROOT)).replace("\\", "/"),
            "--cohort",
            "hybrid_kospi_252d",
            "--require-intersection",
            "--n-folds",
            "3",
            "--min-rows",
            "12",
            "--output",
            str(wf_out),
        ]
    )
    wf = _load(wf_out)
    shadow = wf.get("shadow_metrics") or {}
    return {
        "arm_id": arm_id,
        "macro_source": "carry_forward_merged" if overlay else "vault_observed_fred_join",
        "wide_join_json": str(wide_out.relative_to(ROOT)).replace("\\", "/"),
        "causal_json": str(causal_out.relative_to(ROOT)).replace("\\", "/"),
        "wf_json": str(wf_out.relative_to(ROOT)).replace("\\", "/"),
        "hybrid_macro_join_rate": hy.get("macro_join_rate"),
        "hybrid_flow_join_rate": hy.get("daily_flow_join_rate"),
        "intersection_rows": causal.get("inputs", {}).get("intersection_rows_in_wide"),
        "selected_features": causal.get("selected_features"),
        "mean_test_accuracy": shadow.get("mean_test_accuracy"),
        "mean_majority_baseline": shadow.get("mean_majority_baseline"),
        "delta_minus_majority": shadow.get("delta_minus_majority"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    arms = [
        _arm_pipeline(
            "vault_observed",
            ROOT / "reports/rq025_ab_vault_observed_wide_hypo_v1_latest.json",
            overlay=False,
        ),
        _arm_pipeline(
            "carry_forward",
            ROOT / "reports/rq025_ab_carry_forward_wide_hypo_v1_latest.json",
            overlay=True,
        ),
    ]
    a0, a1 = arms[0], arms[1]
    delta_acc = None
    if isinstance(a0.get("mean_test_accuracy"), (int, float)) and isinstance(
        a1.get("mean_test_accuracy"), (int, float)
    ):
        delta_acc = round(float(a1["mean_test_accuracy"]) - float(a0["mean_test_accuracy"]), 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "arms": arms,
        "comparison": {
            "carry_forward_minus_vault_observed_accuracy": delta_acc,
            "carry_forward_inflates_macro_join": (
                float(a1.get("hybrid_macro_join_rate") or 0)
                > float(a0.get("hybrid_macro_join_rate") or 0)
            ),
            "headline_uplift_claim_allowed": False,
            "note": "carry-forward is join-rate convenience only; not lambda recompute proof",
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} vault_acc={a0.get('mean_test_accuracy')} "
        f"cf_acc={a1.get('mean_test_accuracy')} delta_cf={delta_acc}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
