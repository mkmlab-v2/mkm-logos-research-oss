#!/usr/bin/env python3
"""[HYPO] Chain: upstream λ cert gate → train-only causal → holdout compare vs full-sample causal."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CERT_SCRIPT = ROOT / "scripts/apply_rq025_upstream_lambda_certification_v1.py"
CAUSAL_SCRIPT = ROOT / "scripts/build_rq025_causal_feature_filter_poc_v1.py"
HOLDOUT_SCRIPT = ROOT / "scripts/build_rq025_holdout_2025h2_blind_revalidation_v1.py"
VAULT_WIDE = ROOT / "reports/rq025_vault_macro_direct_wide_hypo_v1_latest.json"
FULL_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_hypo_v1_latest.json"
TRAIN_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_train_only_hypo_v1_latest.json"
HOLDOUT_FULL = ROOT / "reports/rq025_holdout_2025h2_full_causal_v1_latest.json"
HOLDOUT_TRAIN = ROOT / "reports/rq025_holdout_2025h2_train_only_causal_v1_latest.json"
CERT_OUT = ROOT / "reports/rq025_upstream_lambda_certification_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_train_only_causal_holdout_chain_poc_v1_latest.json"
SCHEMA = "rq025_train_only_causal_holdout_chain_poc_v1"
TRAIN_CUTOFF = "2025-06-30"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}\n{proc.stdout}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-cutoff", default=TRAIN_CUTOFF)
    ap.add_argument("--skip-cert-gate", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cert_doc: dict[str, Any] = {}
    if not args.skip_cert_gate:
        _run([sys.executable, str(CERT_SCRIPT)])
        cert_doc = _load(CERT_OUT)

    cutoff = args.train_cutoff[:10]
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
            "--max-eval-date",
            cutoff,
            "--output",
            str(TRAIN_CAUSAL),
        ]
    )
    train_causal = _load(TRAIN_CAUSAL)

    _run(
        [
            sys.executable,
            str(HOLDOUT_SCRIPT),
            "--causal-json",
            str(FULL_CAUSAL),
            "--output",
            str(HOLDOUT_FULL),
        ]
    )
    _run(
        [
            sys.executable,
            str(HOLDOUT_SCRIPT),
            "--causal-json",
            str(TRAIN_CAUSAL),
            "--output",
            str(HOLDOUT_TRAIN),
        ]
    )
    full_h = _load(HOLDOUT_FULL)
    train_h = _load(HOLDOUT_TRAIN)

    full_ens = (full_h.get("full_ensemble") or {})
    train_ens = (train_h.get("full_ensemble") or {})
    delta_test = None
    if full_ens.get("status") == "ok" and train_ens.get("status") == "ok":
        delta_test = round(float(train_ens["test_accuracy"]) - float(full_ens["test_accuracy"]), 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "upstream_lambda_certification": cert_doc if cert_doc else {"skipped": True},
        "train_only_causal": {
            "train_cutoff_max_eval_date": cutoff,
            "output_json": str(TRAIN_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
            "n_selected_features": len(train_causal.get("selected_features") or []),
            "selected_features": train_causal.get("selected_features"),
            "n_train_rows": (train_causal.get("inputs") or {}).get("n_rows"),
        },
        "holdout_full_sample_causal": {
            "causal_json": str(FULL_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
            "artifact": str(HOLDOUT_FULL.relative_to(ROOT)).replace("\\", "/"),
            "ensemble_test_accuracy": full_ens.get("test_accuracy"),
            "delta_minus_majority": full_ens.get("delta_minus_majority"),
        },
        "holdout_train_only_causal": {
            "causal_json": str(TRAIN_CAUSAL.relative_to(ROOT)).replace("\\", "/"),
            "artifact": str(HOLDOUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
            "ensemble_test_accuracy": train_ens.get("test_accuracy"),
            "delta_minus_majority": train_ens.get("delta_minus_majority"),
        },
        "delta_train_only_minus_full_test": delta_test,
        "verdict": {
            "train_only_reduces_leakage_ack": True,
            "train_only_improves_holdout_test": bool(delta_test is not None and delta_test > 0),
            "either_beats_majority": bool(
                (full_ens.get("delta_minus_majority") or -1) > 0
                or (train_ens.get("delta_minus_majority") or -1) > 0
            ),
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
        f"WROTE: {out_path} cert={cert_doc.get('status')} "
        f"full_test={full_ens.get('test_accuracy')} train_only_test={train_ens.get('test_accuracy')} "
        f"delta={delta_test}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
