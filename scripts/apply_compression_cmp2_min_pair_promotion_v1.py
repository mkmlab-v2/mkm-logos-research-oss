#!/usr/bin/env python3
"""Promote cmp2_min_pair to production zone_a_scm (requires saving-floor waiver on disk)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_compression_recommended_policy_chain_v1 import (  # noqa: E402
    ACTIVE_REPORT,
    BASELINE_SOFT,
    CMP2_IDS,
    MIN_PAIR_ADD,
    PIN_EXP,
    PIN_PROD,
    POLICY_FLOOR,
    SCM_BACKUP,
    SCM_SHARD,
    SWEEP_OUT,
    _apply_min_pair,
    _ensure_baseline,
    _load_shard,
    _metrics_from_active,
    _run,
    _soft_terms,
    _write_shard,
)

WAIVER_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_cmp2_min_pair_promotion_waiver_v1.json"
PRODUCTION_SOFT_MIN_PAIR = list(BASELINE_SOFT) + [t for t in MIN_PAIR_ADD if t not in BASELINE_SOFT]


def _write_waiver(*, metrics: dict[str, Any], approver: str) -> None:
    saving = float(metrics["global_token_saving_rate"])
    doc = {
        "schema": "compression_cmp2_min_pair_promotion_waiver_v1",
        "approved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "approver": approver,
        "policy_floor_global_token_saving_rate": POLICY_FLOOR,
        "waived_metric": "ultra_saving_policy_ok",
        "rationale": "Commander approved cmp2_015/023 Jaccard uplift; accept ~0.16pp global saving below 0.47.",
        "production_must_keep_soft_additions": MIN_PAIR_ADD,
        "observed_at_promotion": {
            **metrics,
            "floor_miss_pp": max(0.0, POLICY_FLOOR - saving),
        },
    }
    WAIVER_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _refresh_promoted_artifacts(*, metrics: dict[str, Any], prior_baseline: dict[str, Any] | None) -> None:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    saving = float(metrics["global_token_saving_rate"])
    sweep = {
        "schema": "compression_cmp2_local_mustkeep_sweep_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "track_wall": "compression_production_with_waiver",
        "policy_floor_global_token_saving_rate": POLICY_FLOOR,
        "target_case_ids": list(CMP2_IDS),
        "shard": "codebook/shards/zone_a_scm.json",
        "baseline": prior_baseline or {},
        "variants": [{"id": "cmp2_min_pair", "must_keep_soft_additions": MIN_PAIR_ADD, **metrics}],
        "recommendation": {
            "production_shard": "cmp2_min_pair",
            "research_candidate_id": "cmp2_min_pair",
            "applied_to_production": True,
            "saving_floor_waiver": WAIVER_OUT.relative_to(ROOT).as_posix(),
        },
        "pin_artifacts": {
            "production": "docs/final/artifacts/compression_scm_shard_pin_v1.json",
            "waiver": WAIVER_OUT.relative_to(ROOT).as_posix(),
        },
    }
    SWEEP_OUT.write_text(json.dumps(sweep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pin_prod = {
        "schema": "compression_scm_shard_pin_v1",
        "ts_utc": ts,
        "status": "production_cmp2_min_pair",
        "recommendation": "promoted_with_saving_floor_waiver",
        "production_shard": "codebook/shards/zone_a_scm.json",
        "waiver_artifact": WAIVER_OUT.relative_to(ROOT).as_posix(),
        "cmp2_sweep_artifact": SWEEP_OUT.relative_to(ROOT).as_posix(),
        "active_kpi": {
            **metrics,
            "ultra_saving_policy_min": POLICY_FLOOR,
            "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
            "ultra_saving_policy_waived": True,
            "cmp2_015_jaccard": metrics["cmp2_by_id"].get("cmp2_015"),
            "cmp2_023_jaccard": metrics["cmp2_by_id"].get("cmp2_023"),
        },
    }
    PIN_PROD.write_text(json.dumps(pin_prod, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pin_exp = {
        "schema": "compression_scm_shard_pin_experimental_v1",
        "ts_utc": ts,
        "recommendation": "promoted_to_production",
        "note": "cmp2_min_pair merged into production shard; see waiver artifact.",
        "waiver_artifact": WAIVER_OUT.relative_to(ROOT).as_posix(),
    }
    PIN_EXP.write_text(json.dumps(pin_exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approver", default="commander", help="Waiver approver label")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--capture-baseline-first", action="store_true", help="Bench baseline once before promote")
    args = ap.parse_args()
    py = sys.executable

    prior_baseline: dict[str, Any] | None = None
    if args.capture_baseline_first and _soft_terms(_load_shard()) != PRODUCTION_SOFT_MIN_PAIR:
        _ensure_baseline()
        if _run([py, "scripts/run_ultra_compression_default.py"]) != 0:
            return 1
        prior_baseline = _metrics_from_active()

    if not SCM_BACKUP.is_file():
        SCM_BACKUP.write_text(SCM_SHARD.read_text(encoding="utf-8"), encoding="utf-8")

    _apply_min_pair()
    if _soft_terms(_load_shard()) != PRODUCTION_SOFT_MIN_PAIR:
        print("FAIL: shard soft terms mismatch after promote", file=sys.stderr)
        return 2

    if _run([py, "scripts/run_ultra_compression_default.py"]) != 0:
        return 1
    if _run([py, "scripts/report_ultra_compression_kpi_summary.py"]) != 0:
        return 1
    if _run([py, "scripts/report_compression_jaccard_loss_patterns.py", "--sla-track", "universal"]) != 0:
        return 1

    metrics = _metrics_from_active()
    _write_waiver(metrics=metrics, approver=args.approver)
    _refresh_promoted_artifacts(metrics=metrics, prior_baseline=prior_baseline)

    if not args.skip_pytest:
        tests = [
            "tests/test_compression_recommended_policy_chain_v1.py",
            "tests/test_compression_token_api_v2_stub.py",
        ]
        if _run([py, "-m", "pytest", *tests, "-q", "--tb=short"]) != 0:
            return 1

    print(
        f"OK promoted saving={metrics['global_token_saving_rate']:.4f} "
        f"cmp2_015={metrics['cmp2_by_id'].get('cmp2_015')} "
        f"waiver={WAIVER_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
