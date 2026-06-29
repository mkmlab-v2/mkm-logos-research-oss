#!/usr/bin/env python3
"""[HYPO] Compare lambda macro sources: proxy vs merged-substitute vs upstream (if provided)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WIDE_SCRIPT = ROOT / "scripts/build_rq025_flow_fred_wide_join_hypo_v1.py"
CAUSAL_SCRIPT = ROOT / "scripts/build_rq025_causal_feature_filter_poc_v1.py"
HOLDOUT_SCRIPT = ROOT / "scripts/build_rq025_holdout_2025h2_blind_revalidation_v1.py"
OVERFIT_SCRIPT = ROOT / "scripts/build_rq025_layer5_ensemble_overfit_audit_v1.py"
DEFAULT_OUT = ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json"
SCHEMA = "rq025_lambda_source_three_arm_compare_v1"
ARM_DIR = ROOT / "reports/rq025_three_arm"
PROXY_CSV = ROOT / "reports/backups/sgp_history_master_real_pre_cert_20260611T074914Z.csv"
MERGED_VAULT = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
BASELINE = ROOT / "reports/rq025_holdout_overfit_baseline_proxy_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}\n{proc.stdout}")


def _eval_arm(
    arm_id: str,
    *,
    macro_csv: Path,
    label: str,
    upstream_production: bool,
) -> dict[str, Any]:
    ARM_DIR.mkdir(parents=True, exist_ok=True)
    wide_out = ARM_DIR / f"wide_{arm_id}_hypo_v1_latest.json"
    causal_out = ARM_DIR / f"causal_{arm_id}_hypo_v1_latest.json"
    holdout_out = ARM_DIR / f"holdout_{arm_id}_v1_latest.json"
    overfit_out = ARM_DIR / f"overfit_{arm_id}_v1_latest.json"

    if not macro_csv.is_file():
        return {
            "arm_id": arm_id,
            "label": label,
            "status": "missing_macro_csv",
            "macro_csv": str(macro_csv),
            "upstream_production_batch": upstream_production,
        }

    _run(
        [
            sys.executable,
            str(WIDE_SCRIPT),
            "--macro-source",
            "vault_csv",
            "--macro-csv",
            str(macro_csv),
            "--output",
            str(wide_out),
        ]
    )
    wide = _load(wide_out)
    hy = (wide.get("cohorts") or {}).get("hybrid_kospi_252d") or {}

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
    _run(
        [
            sys.executable,
            str(HOLDOUT_SCRIPT),
            "--wide-join-json",
            str(wide_out),
            "--causal-json",
            str(causal_out),
            "--output",
            str(holdout_out),
        ]
    )
    _run(
        [
            sys.executable,
            str(OVERFIT_SCRIPT),
            "--wide-join-json",
            str(wide_out),
            "--causal-json",
            str(causal_out),
            "--output",
            str(overfit_out),
        ]
    )
    holdout = _load(holdout_out)
    overfit = _load(overfit_out)
    ens = holdout.get("full_ensemble") or {}
    causal = _load(causal_out)

    return {
        "arm_id": arm_id,
        "label": label,
        "status": "ok",
        "upstream_production_batch": upstream_production,
        "macro_csv": str(macro_csv),
        "macro_join_rate": hy.get("macro_join_rate"),
        "n_selected_features": len(causal.get("selected_features") or []),
        "holdout_ensemble_test": ens.get("test_accuracy"),
        "holdout_baseline_test": (holdout.get("causal_baseline") or {}).get("test_accuracy"),
        "holdout_delta_minus_majority": ens.get("delta_minus_majority"),
        "overfit_suspected": (overfit.get("verdict") or {}).get("overfit_suspected"),
        "p_over_n": overfit.get("p_over_n"),
        "artifacts": {
            "wide": str(wide_out.relative_to(ROOT)).replace("\\", "/"),
            "causal": str(causal_out.relative_to(ROOT)).replace("\\", "/"),
            "holdout": str(holdout_out.relative_to(ROOT)).replace("\\", "/"),
            "overfit": str(overfit_out.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream-csv", type=Path, default=None)
    ap.add_argument(
        "--upstream-label",
        default="upstream_production_csv",
        help="Arm label when upstream CSV is provided",
    )
    ap.add_argument(
        "--upstream-production-batch",
        action="store_true",
        help="Mark upstream arm as off-repo production batch (default: research substitute)",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    upstream_path: Path | None = None
    if args.upstream_csv:
        upstream_path = args.upstream_csv if args.upstream_csv.is_absolute() else ROOT / args.upstream_csv
    elif os.environ.get("RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"):
        upstream_path = Path(os.environ["RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"])

    upstream_label = str(args.upstream_label or "upstream_production_csv")
    upstream_prod = bool(args.upstream_production_batch)

    arms_spec = [
        (
            "proxy",
            "proxy_kospi_calibrated_tail",
            PROXY_CSV,
            False,
        ),
        (
            "merged_substitute",
            "local_merged_carry_forward_substitute",
            MERGED_VAULT,
            False,
        ),
    ]
    if upstream_path and upstream_path.is_file():
        arms_spec.append(("upstream", upstream_label, upstream_path, upstream_prod))

    arms: list[dict[str, Any]] = []
    for arm_id, label, csv_path, is_upstream in arms_spec:
        arms.append(_eval_arm(arm_id, macro_csv=csv_path, label=label, upstream_production=is_upstream))

    baseline = _load(BASELINE).get("metrics") or {}
    proxy_holdout = next((a.get("holdout_ensemble_test") for a in arms if a.get("arm_id") == "proxy"), None)
    merged_holdout = next((a.get("holdout_ensemble_test") for a in arms if a.get("arm_id") == "merged_substitute"), None)
    upstream_holdout = next((a.get("holdout_ensemble_test") for a in arms if a.get("arm_id") == "upstream"), None)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "frozen_proxy_baseline_metrics": baseline,
        "arms": arms,
        "pairwise_delta_holdout_ensemble_test": {
            "merged_minus_proxy": _num_delta(merged_holdout, proxy_holdout),
            "merged_minus_frozen_baseline": _num_delta(merged_holdout, baseline.get("holdout_ensemble_test")),
            "upstream_minus_proxy": _num_delta(upstream_holdout, proxy_holdout),
            "upstream_minus_merged": _num_delta(upstream_holdout, merged_holdout),
        },
        "upstream_arm": {
            "requested": upstream_path is not None,
            "present": bool(upstream_path and upstream_path.is_file()),
            "path": str(upstream_path) if upstream_path else None,
            "label": upstream_label if upstream_path else None,
            "upstream_production_batch": upstream_prod if upstream_path else None,
        },
        "verdict": {
            "any_beats_majority": any(
                float(a.get("holdout_delta_minus_majority") or -1) > 0 for a in arms if a.get("status") == "ok"
            ),
            "best_arm_by_holdout": max(
                (a for a in arms if a.get("status") == "ok"),
                key=lambda a: float(a.get("holdout_ensemble_test") or 0),
                default={},
            ).get("arm_id"),
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
    print(f"WROTE: {out_path} arms={len(arms)} best={payload['verdict']['best_arm_by_holdout']}")
    return 0


def _num_delta(new: Any, old: Any) -> float | None:
    try:
        if new is None or old is None:
            return None
        return round(float(new) - float(old), 6)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
