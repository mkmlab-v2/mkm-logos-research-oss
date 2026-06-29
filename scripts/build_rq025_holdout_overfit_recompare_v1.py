#!/usr/bin/env python3
"""[HYPO] Re-run holdout + overfit + train-only causal; delta vs frozen baseline snapshot."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_SCRIPT = ROOT / "scripts/build_rq025_holdout_2025h2_blind_revalidation_v1.py"
OVERFIT_SCRIPT = ROOT / "scripts/build_rq025_layer5_ensemble_overfit_audit_v1.py"
TRAIN_CHAIN = ROOT / "scripts/build_rq025_train_only_causal_holdout_chain_poc_v1.py"
DEFAULT_BASELINE = ROOT / "reports/rq025_holdout_overfit_baseline_proxy_v1.json"
DEFAULT_OUT = ROOT / "reports/rq025_holdout_overfit_recompare_v1_latest.json"
SCHEMA = "rq025_holdout_overfit_recompare_v1"


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


def _metrics_bundle() -> dict[str, Any]:
    holdout = _load(ROOT / "reports/rq025_holdout_2025h2_blind_revalidation_v1_latest.json")
    overfit = _load(ROOT / "reports/rq025_layer5_ensemble_overfit_audit_v1_latest.json")
    train = _load(ROOT / "reports/rq025_train_only_causal_holdout_chain_poc_v1_latest.json")
    ens = holdout.get("full_ensemble") or {}
    base = holdout.get("causal_baseline") or {}
    return {
        "holdout_ensemble_test": ens.get("test_accuracy"),
        "holdout_baseline_test": base.get("test_accuracy"),
        "holdout_delta_minus_majority": ens.get("delta_minus_majority"),
        "overfit_suspected": (overfit.get("verdict") or {}).get("overfit_suspected"),
        "p_over_n": overfit.get("p_over_n"),
        "mean_train_minus_test_gap": (overfit.get("full_ensemble") or {}).get("mean_train_minus_test_gap"),
        "train_only_ensemble_test": (train.get("holdout_train_only_causal") or {}).get("ensemble_test_accuracy"),
        "train_only_delta_minus_full": train.get("delta_train_only_minus_full_test"),
        "lambda_cert_status": (
            (train.get("upstream_lambda_certification") or {}).get("status")
            or (_load(ROOT / "reports/rq025_upstream_lambda_certification_v1_latest.json").get("status"))
        ),
    }


def _delta(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in current.items():
        if k == "lambda_cert_status":
            out[k] = {"baseline": baseline.get(k), "current": v}
            continue
        b = baseline.get(k)
        if isinstance(v, (int, float)) and isinstance(b, (int, float)):
            out[k] = round(float(v) - float(b), 6)
        elif v != b:
            out[k] = {"baseline": b, "current": v}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-json", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--freeze-baseline", action="store_true", help="Write current metrics as baseline and exit")
    ap.add_argument("--skip-cert-gate", action="store_true", default=True)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    baseline_path = args.baseline_json if args.baseline_json.is_absolute() else ROOT / args.baseline_json
    if args.freeze_baseline or not baseline_path.is_file():
        snap = {
            "schema": "rq025_holdout_overfit_baseline_v1",
            "frozen_at_utc": _utc_now(),
            "lambda_state": "proxy_tail_uncertified",
            "metrics": _metrics_bundle(),
        }
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.freeze_baseline:
            print(f"FROZE baseline: {baseline_path}")
            return 0

    baseline_doc = _load(baseline_path)
    baseline_metrics = baseline_doc.get("metrics") or baseline_doc

    _run([sys.executable, str(HOLDOUT_SCRIPT)])
    _run([sys.executable, str(OVERFIT_SCRIPT)])
    train_cmd = [sys.executable, str(TRAIN_CHAIN)]
    if args.skip_cert_gate:
        train_cmd.append("--skip-cert-gate")
    _run(train_cmd)

    current = _metrics_bundle()
    deltas = _delta(baseline_metrics, current)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "baseline_json": str(baseline_path.relative_to(ROOT)).replace("\\", "/"),
        "baseline_frozen_at_utc": baseline_doc.get("frozen_at_utc"),
        "baseline_lambda_state": baseline_doc.get("lambda_state", "unknown"),
        "baseline_metrics": baseline_metrics,
        "current_metrics": current,
        "delta_current_minus_baseline": deltas,
        "verdict": {
            "material_holdout_change": abs(float(deltas.get("holdout_ensemble_test") or 0)) >= 0.01,
            "overfit_status_changed": deltas.get("overfit_suspected") is not None
            and isinstance(deltas.get("overfit_suspected"), dict),
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
        f"WROTE: {out_path} holdout_delta={deltas.get('holdout_ensemble_test')} "
        f"cert={current.get('lambda_cert_status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
