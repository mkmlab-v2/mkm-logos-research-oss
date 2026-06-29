#!/usr/bin/env python3
"""[HYPO] Vault CSV as primary macro source — wide join + intersection causal + WF smoke."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WIDE_SCRIPT = ROOT / "scripts/build_rq025_flow_fred_wide_join_hypo_v1.py"
CAUSAL_SCRIPT = ROOT / "scripts/build_rq025_causal_feature_filter_poc_v1.py"
WF_SCRIPT = ROOT / "scripts/build_rq025_gbdt_shadow_hypo_v1.py"
DEFAULT_OUT = ROOT / "reports/rq025_vault_macro_direct_wide_join_poc_v1_latest.json"
SCHEMA = "rq025_vault_macro_direct_wide_join_poc_v1"
VAULT_WIDE = ROOT / "reports/rq025_vault_macro_direct_wide_hypo_v1_latest.json"
VAULT_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_hypo_v1_latest.json"
VAULT_WF = ROOT / "reports/rq025_vault_macro_direct_wf_hypo_v1_latest.json"
FRED_WIDE = ROOT / "reports/rq025_vault_only_wide_hypo_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    _run(
        [
            sys.executable,
            str(WIDE_SCRIPT),
            "--macro-source",
            "vault_csv",
            "--output",
            str(VAULT_WIDE),
        ]
    )
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

    fred_compare: dict[str, Any] = {}
    if FRED_WIDE.is_file():
        fred_wide = _load(FRED_WIDE)
        fred_hy = (fred_wide.get("cohorts") or {}).get("hybrid_kospi_252d") or {}
        fred_compare = {
            "fred_arm_wide_json": str(FRED_WIDE.relative_to(ROOT)).replace("\\", "/"),
            "fred_macro_join_rate": fred_hy.get("macro_join_rate"),
            "vault_minus_fred_macro_join_rate": (
                round(float(hy.get("macro_join_rate") or 0) - float(fred_hy.get("macro_join_rate") or 0), 6)
                if fred_hy.get("macro_join_rate") is not None
                else None
            ),
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "macro_source": "vault_csv",
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
        "fred_arm_compare": fred_compare,
        "verdict": {
            "vault_direct_improves_join": (
                float(hy.get("macro_join_rate") or 0) > float((fred_compare or {}).get("fred_macro_join_rate") or 0)
            ),
            "gate_0_55_pass": float(shadow.get("mean_test_accuracy") or 0) >= 0.55,
            "beats_majority_baseline": float(shadow.get("mean_test_accuracy") or 0)
            > float(shadow.get("mean_majority_baseline") or 1),
            "track_a_promotion": False,
            "note": "Vault CSV includes proxy-appended tail; not upstream-certified lambda",
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
        f"WROTE: {out_path} macro_join={hy.get('macro_join_rate')} "
        f"acc={shadow.get('mean_test_accuracy')} delta_maj={shadow.get('delta_minus_majority')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
