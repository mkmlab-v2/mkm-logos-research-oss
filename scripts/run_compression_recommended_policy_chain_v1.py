#!/usr/bin/env python3
"""M-COMP-A1: enforce production baseline shard + auto-refresh research cmp2_min_pair metrics."""

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

SCM_SHARD = ROOT / "codebook" / "shards" / "zone_a_scm.json"
SCM_BACKUP = ROOT / "codebook" / "shards" / "zone_a_scm.json.bak_20260518_cmp2_local"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
SWEEP_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_cmp2_local_mustkeep_sweep_20260518_v1.json"
PIN_PROD = ROOT / "docs" / "final" / "artifacts" / "compression_scm_shard_pin_v1.json"
PIN_EXP = ROOT / "docs" / "final" / "artifacts" / "compression_scm_shard_pin_experimental_v1.json"
POLICY_FLOOR = 0.47
BASELINE_SOFT = ["증상", "처방", "금칙", "단위", "안전하다"]
MIN_PAIR_ADD = ["일반화하면", "손실되면"]
PRODUCTION_SOFT_MIN_PAIR = list(BASELINE_SOFT) + [t for t in MIN_PAIR_ADD if t not in BASELINE_SOFT]
WAIVER_PATH = ROOT / "docs" / "final" / "artifacts" / "compression_cmp2_min_pair_promotion_waiver_v1.json"
CMP2_IDS = ("cmp2_015", "cmp2_023")


def _is_promoted_production() -> bool:
    if WAIVER_PATH.is_file():
        return True
    try:
        return _soft_terms(_load_shard()) == PRODUCTION_SOFT_MIN_PAIR
    except OSError:
        return False


def _load_shard() -> dict[str, Any]:
    return json.loads(SCM_SHARD.read_text(encoding="utf-8"))


def _write_shard(doc: dict[str, Any]) -> None:
    SCM_SHARD.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _soft_terms(doc: dict[str, Any]) -> list[str]:
    return list(doc.get("must_keep_soft_terms") or [])


def _ensure_baseline() -> None:
    doc = _load_shard()
    soft = _soft_terms(doc)
    if soft == BASELINE_SOFT:
        return
    if SCM_BACKUP.is_file():
        backup = json.loads(SCM_BACKUP.read_text(encoding="utf-8"))
        if _soft_terms(backup) == BASELINE_SOFT:
            _write_shard(backup)
            return
    doc["must_keep_soft_terms"] = list(BASELINE_SOFT)
    _write_shard(doc)


def _apply_min_pair() -> dict[str, Any]:
    doc = _load_shard()
    merged = list(BASELINE_SOFT)
    for t in MIN_PAIR_ADD:
        if t not in merged:
            merged.append(t)
    doc["must_keep_soft_terms"] = merged
    _write_shard(doc)
    return doc


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _metrics_from_active() -> dict[str, Any]:
    report = json.loads(ACTIVE_REPORT.read_text(encoding="utf-8"))
    cm = report.get("compression_metrics") or {}
    cases = {str(c.get("id")): c for c in (cm.get("cases") or [])}
    saving = float(cm.get("global_token_saving_rate") or 0)
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard") or 0),
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "cmp2_by_id": {
            cid: float((cases.get(cid) or {}).get("reconstruction_fidelity_jaccard") or 0) for cid in CMP2_IDS
        },
    }


def _refresh_artifacts(*, baseline: dict[str, Any], research: dict[str, Any]) -> None:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sweep = {
        "schema": "compression_cmp2_local_mustkeep_sweep_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "policy_floor_global_token_saving_rate": POLICY_FLOOR,
        "target_case_ids": list(CMP2_IDS),
        "shard": "codebook/shards/zone_a_scm.json",
        "baseline": {**baseline, "must_keep_soft_additions": []},
        "variants": [
            {
                "id": "cmp2_min_pair",
                "must_keep_soft_additions": MIN_PAIR_ADD,
                **research,
            }
        ],
        "recommendation": {
            "production_shard": "keep_baseline",
            "research_candidate_id": "cmp2_min_pair",
            "applied_to_production": False,
            "rationale": "Auto-chain: production stays baseline (saving floor). cmp2_min_pair metrics refreshed without promoting shard.",
        },
        "pin_artifacts": {
            "production": "docs/final/artifacts/compression_scm_shard_pin_v1.json",
            "experimental": "docs/final/artifacts/compression_scm_shard_pin_experimental_v1.json",
        },
    }
    SWEEP_OUT.write_text(json.dumps(sweep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pin_prod = {
        "schema": "compression_scm_shard_pin_v1",
        "ts_utc": ts,
        "status": "production_baseline",
        "recommendation": "keep_baseline",
        "production_shard": "codebook/shards/zone_a_scm.json",
        "experimental_artifact": "docs/final/artifacts/compression_scm_shard_pin_experimental_v1.json",
        "cmp2_sweep_artifact": SWEEP_OUT.relative_to(ROOT).as_posix(),
        "active_kpi": {
            **baseline,
            "ultra_saving_policy_min": POLICY_FLOOR,
            "cmp2_015_jaccard": baseline["cmp2_by_id"].get("cmp2_015"),
            "cmp2_023_jaccard": baseline["cmp2_by_id"].get("cmp2_023"),
        },
    }
    PIN_PROD.write_text(json.dumps(pin_prod, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    floor_miss = max(0.0, POLICY_FLOOR - float(research["global_token_saving_rate"]))
    pin_exp = {
        "schema": "compression_scm_shard_pin_experimental_v1",
        "ts_utc": ts,
        "recommendation": "cmp2_min_pair_research_only",
        "sweep_ssot": SWEEP_OUT.relative_to(ROOT).as_posix(),
        "variants": [
            {
                "id": "cmp2_min_pair",
                "status": "recommended_research_candidate",
                "must_keep_soft_additions": MIN_PAIR_ADD,
                "cmp2_015_jaccard": research["cmp2_by_id"].get("cmp2_015"),
                "cmp2_023_jaccard": research["cmp2_by_id"].get("cmp2_023"),
                "global_token_saving_rate": research["global_token_saving_rate"],
                "ultra_saving_policy_ok": research["ultra_saving_policy_ok"],
                "floor_miss_pp": floor_miss,
            }
        ],
    }
    PIN_EXP.write_text(json.dumps(pin_exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-loss-patterns", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument(
        "--promote-min-pair",
        action="store_true",
        help="Delegate to apply_compression_cmp2_min_pair_promotion_v1.py (saving-floor waiver).",
    )
    args = ap.parse_args()
    py = sys.executable

    if args.promote_min_pair:
        cmd = [py, "scripts/apply_compression_cmp2_min_pair_promotion_v1.py", "--capture-baseline-first"]
        if args.skip_pytest:
            cmd.append("--skip-pytest")
        return _run(cmd)

    if _is_promoted_production():
        from scripts.apply_compression_cmp2_min_pair_promotion_v1 import _refresh_promoted_artifacts

        if _soft_terms(_load_shard()) != PRODUCTION_SOFT_MIN_PAIR:
            _apply_min_pair()
        if _run([py, "scripts/run_ultra_compression_default.py"]) != 0:
            return 1
        if _run([py, "scripts/report_ultra_compression_kpi_summary.py"]) != 0:
            return 1
        if not args.skip_loss_patterns:
            if _run([py, "scripts/report_compression_jaccard_loss_patterns.py", "--sla-track", "universal"]) != 0:
                return 1
        prod = _metrics_from_active()
        prior_baseline: dict[str, Any] | None = None
        if SWEEP_OUT.is_file():
            prior_baseline = (json.loads(SWEEP_OUT.read_text(encoding="utf-8")) or {}).get("baseline")
        _refresh_promoted_artifacts(metrics=prod, prior_baseline=prior_baseline)
        if not args.skip_pytest:
            if _run([py, "-m", "pytest", "tests/test_compression_recommended_policy_chain_v1.py", "-q", "--tb=short"]) != 0:
                return 1
        print(f"OK promoted-production saving={prod['global_token_saving_rate']:.4f}")
        return 0

    _ensure_baseline()

    if _run([py, "scripts/run_ultra_compression_default.py"]) != 0:
        return 1
    if _run([py, "scripts/report_ultra_compression_kpi_summary.py"]) != 0:
        return 1
    if not args.skip_loss_patterns:
        if _run([py, "scripts/report_compression_jaccard_loss_patterns.py", "--sla-track", "universal"]) != 0:
            return 1
    baseline = _metrics_from_active()
    if not baseline["ultra_saving_policy_ok"]:
        print("FAIL: baseline ultra_saving_policy_ok=false", file=sys.stderr)
        return 2

    _apply_min_pair()
    try:
        if _run([py, "scripts/run_ultra_compression_default.py"]) != 0:
            return 1
        research = _metrics_from_active()
    finally:
        _ensure_baseline()

    _refresh_artifacts(baseline=baseline, research=research)

    if not args.skip_pytest:
        if _run([py, "-m", "pytest", "tests/test_compression_recommended_policy_chain_v1.py", "-q", "--tb=short"]) != 0:
            return 1

    print(
        f"OK baseline saving={baseline['global_token_saving_rate']:.4f} "
        f"research saving={research['global_token_saving_rate']:.4f} "
        f"cmp2_015={research['cmp2_by_id'].get('cmp2_015')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
