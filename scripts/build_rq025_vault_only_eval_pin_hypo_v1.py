#!/usr/bin/env python3
"""[HYPO] Pin Oracle RQ-025 eval to vault_observed arm; ban carry-forward for headline claims."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_vault_only_eval_pin_hypo_v1_latest.json"
SCHEMA = "rq025_vault_only_eval_pin_hypo_v1"
WIDE_SCRIPT = ROOT / "scripts/build_rq025_flow_fred_wide_join_hypo_v1.py"
CAUSAL_SCRIPT = ROOT / "scripts/build_rq025_causal_feature_filter_poc_v1.py"
WF_SCRIPT = ROOT / "scripts/build_rq025_gbdt_shadow_hypo_v1.py"
AB_JSON = ROOT / "reports/rq025_macro_carryforward_sensitivity_ab_v1_latest.json"
VAULT_WIDE = ROOT / "reports/rq025_vault_only_wide_hypo_v1_latest.json"
VAULT_CAUSAL = ROOT / "reports/rq025_vault_only_causal_hypo_v1_latest.json"
VAULT_WF = ROOT / "reports/rq025_vault_only_wf_hypo_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}")


def _vault_pipeline() -> dict[str, Any]:
    _run([sys.executable, str(WIDE_SCRIPT), "--output", str(VAULT_WIDE)])
    wide = _load(VAULT_WIDE)
    hy = (wide.get("cohorts") or {}).get("hybrid_kospi_252d") or {}
    _run(
        [
            sys.executable,
            str(CAUSAL_SCRIPT),
            "--wide-join-json",
            str(VAULT_WIDE.relative_to(ROOT)).replace("\\", "/"),
            "--cohort",
            "hybrid_kospi_252d",
            "--feature-set",
            "all",
            "--profile",
            "hybrid_relaxed",
            "--require-intersection",
            "--output",
            str(VAULT_CAUSAL),
        ]
    )
    causal = _load(VAULT_CAUSAL)
    _run(
        [
            sys.executable,
            str(WF_SCRIPT),
            "--wide-join-json",
            str(VAULT_WIDE.relative_to(ROOT)).replace("\\", "/"),
            "--causal-json",
            str(VAULT_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
            "--cohort",
            "hybrid_kospi_252d",
            "--require-intersection",
            "--n-folds",
            "3",
            "--min-rows",
            "12",
            "--output",
            str(VAULT_WF),
        ]
    )
    wf = _load(VAULT_WF)
    shadow = wf.get("shadow_metrics") or {}
    return {
        "wide_join_json": str(VAULT_WIDE.relative_to(ROOT)).replace("\\", "/"),
        "causal_json": str(VAULT_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
        "wf_json": str(VAULT_WF.relative_to(ROOT)).replace("\\", "/"),
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
    ap.add_argument("--skip-rerun", action="store_true", help="Use existing vault_only artifacts if present")
    args = ap.parse_args(argv)

    vault_metrics = _vault_pipeline() if not args.skip_rerun else {}
    if args.skip_rerun and VAULT_WF.is_file():
        wf = _load(VAULT_WF)
        causal = _load(VAULT_CAUSAL) if VAULT_CAUSAL.is_file() else {}
        wide = _load(VAULT_WIDE) if VAULT_WIDE.is_file() else {}
        hy = (wide.get("cohorts") or {}).get("hybrid_kospi_252d") or {}
        shadow = wf.get("shadow_metrics") or {}
        vault_metrics = {
            "wide_join_json": str(VAULT_WIDE.relative_to(ROOT)).replace("\\", "/"),
            "causal_json": str(VAULT_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
            "wf_json": str(VAULT_WF.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_macro_join_rate": hy.get("macro_join_rate"),
            "hybrid_flow_join_rate": hy.get("daily_flow_join_rate"),
            "intersection_rows": causal.get("inputs", {}).get("intersection_rows_in_wide"),
            "selected_features": causal.get("selected_features"),
            "mean_test_accuracy": shadow.get("mean_test_accuracy"),
            "mean_majority_baseline": shadow.get("mean_majority_baseline"),
            "delta_minus_majority": shadow.get("delta_minus_majority"),
        }

    ab_ref: dict[str, Any] = {}
    if AB_JSON.is_file():
        ab = _load(AB_JSON)
        arms = {a.get("arm_id"): a for a in ab.get("arms") or [] if isinstance(a, dict)}
        ab_ref = {
            "pointer": str(AB_JSON.relative_to(ROOT)).replace("\\", "/"),
            "vault_observed_accuracy": (arms.get("vault_observed") or {}).get("mean_test_accuracy"),
            "carry_forward_accuracy": (arms.get("carry_forward") or {}).get("mean_test_accuracy"),
            "carry_forward_inflates_join": (ab.get("comparison") or {}).get(
                "carry_forward_inflates_macro_join"
            ),
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "policy": {
            "default_eval_arm": "vault_observed",
            "carry_forward_arm": "research_only_forbidden_headline",
            "wide_join_flags_banned_for_ssot": ["--macro-csv-overlay", "--macro-csv"],
            "reason": (
                "Carry-forward inflates macro join and WF without lambda recompute; "
                "vault_observed is the conservative SSOT for Oracle B-track claims."
            ),
        },
        "vault_observed_metrics": vault_metrics,
        "ab_sensitivity_reference": ab_ref,
        "verdict": {
            "gate_0_55_pass": False,
            "beats_majority_baseline": (
                float(vault_metrics.get("mean_test_accuracy") or 0)
                > float(vault_metrics.get("mean_majority_baseline") or 1)
            ),
            "headline_uplift_claim_allowed": False,
            "track_a_promotion": False,
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
        f"WROTE: {out_path} vault_acc={vault_metrics.get('mean_test_accuracy')} "
        f"macro_join={vault_metrics.get('hybrid_macro_join_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
