#!/usr/bin/env python3
"""Commander-approved chain: logos per-lane cap dryrun + golden_core regression + promote candidate."""

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

DEFAULT_POLICY = ROOT / "reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json"
DEFAULT_LOGOS_LANE = ROOT / "reports/golden_40_logos_verse_compression_lane_stride120_v1.json"
LOGOS_OUT = ROOT / "reports/golden_40_expansion_dryrun_logos_cap015_v1_latest.json"
GOLDEN_OUT = ROOT / "reports/golden_40_expansion_dryrun_golden_core_cap_regression_v1_latest.json"
PROMOTE_OUT = ROOT / "reports/logos_verse_per_lane_cap_promote_candidate_v1_latest.json"
SIGNOFF_APPEND = ROOT / "reports/logos_verse_per_lane_cap_commander_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, tail[-2000:]


def _golden_core_jaccard(doc: dict[str, Any]) -> float | None:
    for tier in reversed(doc.get("tiers") or []):
        gc = tier.get("golden_core_only_metrics") or {}
        j = gc.get("avg_reconstruction_fidelity_jaccard")
        if j is not None:
            return float(j)
        if tier.get("target_case_count") == 40:
            m = tier.get("aggregate_metrics") or {}
            return float(m.get("avg_reconstruction_fidelity_jaccard") or 0) or None
    return None


def _blended_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    tier = None
    for t in doc.get("tiers") or []:
        if int(t.get("target_case_count") or 0) >= int(t.get("actual_case_count") or 0):
            tier = t
    tier = tier or ((doc.get("tiers") or [])[-1] if doc.get("tiers") else {})
    m = tier.get("aggregate_metrics") or {}
    return {
        "target_case_count": tier.get("target_case_count"),
        "actual_case_count": tier.get("actual_case_count"),
        "mean_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        "mean_saving": m.get("global_token_saving_rate"),
        "floor_regression_ok": tier.get("floor_regression_ok"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Logos per-lane cap promote chain (B-track)")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--logos-lane", type=Path, default=DEFAULT_LOGOS_LANE)
    ap.add_argument("--target-counts", default="240")
    ap.add_argument("--skip-audit", action="store_true")
    args = ap.parse_args()

    from scripts.logos_verse_per_lane_ssot_cap_policy_v1 import load_policy

    policy = load_policy(args.policy if args.policy.is_absolute() else ROOT / args.policy)
    gates = policy.get("promotion_gates") or {}

    steps: list[dict[str, Any]] = []

    if not args.skip_audit:
        ec, tail = _run([sys.executable, "scripts/audit_wire_atom_gloss_index_alignment_v1.py"])
        steps.append({"step": "wire_atom_gloss_audit", "exit_code": ec, "tail": tail})

    logos_lane = args.logos_lane if args.logos_lane.is_absolute() else ROOT / args.logos_lane
    ec_logos, tail_logos = _run(
        [
            sys.executable,
            "scripts/run_golden40_expansion_dryrun_v1.py",
            "--pool-mode",
            "homogeneous_logos_verse",
            "--logos-verse-lane",
            str(logos_lane),
            "--target-counts",
            args.target_counts,
            "--apply-per-lane-cap-policy",
            "--per-lane-cap-policy",
            str(args.policy if args.policy.is_absolute() else ROOT / args.policy),
            "--out-json",
            str(LOGOS_OUT),
        ]
    )
    steps.append({"step": "logos_homogeneous_cap_dryrun", "exit_code": ec_logos, "tail": tail_logos})

    ec_gc, tail_gc = _run(
        [
            sys.executable,
            "scripts/run_golden40_expansion_dryrun_v1.py",
            "--pool-mode",
            "golden_core_only",
            "--target-counts",
            "40",
            "--out-json",
            str(GOLDEN_OUT),
        ]
    )
    steps.append({"step": "golden_core_regression", "exit_code": ec_gc, "tail": tail_gc})

    logos_doc = json.loads(LOGOS_OUT.read_text(encoding="utf-8")) if LOGOS_OUT.is_file() else {}
    golden_doc = json.loads(GOLDEN_OUT.read_text(encoding="utf-8")) if GOLDEN_OUT.is_file() else {}

    logos_m = _blended_metrics(logos_doc)
    gc_j = _golden_core_jaccard(golden_doc)

    logos_j_min = float(gates.get("logos_lane_jaccard_min") or 0.87)
    gc_j_min = float(gates.get("golden_core_jaccard_min") or 0.873)
    logos_s_min = float(gates.get("logos_lane_saving_min") or 0.45)

    logos_j = float(logos_m.get("mean_jaccard") or 0)
    logos_s = float(logos_m.get("mean_saving") or 0)
    gc_eps = float(gates.get("golden_core_jaccard_epsilon") or 0.001)

    logos_lane_ok = (
        ec_logos == 0
        and logos_j >= logos_j_min
        and logos_s >= logos_s_min
        and bool(logos_m.get("floor_regression_ok"))
    )
    golden_core_ok = ec_gc == 0 and gc_j is not None and gc_j + gc_eps >= gc_j_min
    gates_ok = logos_lane_ok and golden_core_ok

    promote_doc: dict[str, Any] = {
        "schema": "logos_verse_per_lane_cap_promote_candidate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "would_change_active": False,
        "commander_approved_per_lane_cap": True,
        "policy_path": str((args.policy if args.policy.is_absolute() else ROOT / args.policy).relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "headline_rule": policy.get("headline_rule"),
        "logos_lane_metrics": logos_m,
        "golden_core_jaccard": gc_j,
        "promotion_gates": gates,
        "logos_lane_gates_passed": logos_lane_ok,
        "golden_core_regression_passed": golden_core_ok,
        "gates_passed": gates_ok,
        "per_lane_promote_ok": logos_lane_ok,
        "active_write_authorized": False,
        "ms_paste_authorized": False,
        "artifacts": {
            "logos_dryrun": str(LOGOS_OUT.relative_to(ROOT)).replace("\\", "/"),
            "golden_core_dryrun": str(GOLDEN_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
        "next": (
            "Per-lane B-track KPI registered; ACTIVE/MS unchanged (FAIL-COMP-004)."
            if gates_ok
            else "Fix failing step or relax gates in policy JSON; no promote."
        ),
    }
    PROMOTE_OUT.write_text(json.dumps(promote_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "logos_verse_per_lane_cap_commander_signoff_v1",
        "signoff_utc": _utc(),
        "approved": {
            "logos_per_lane_ssot_cap_btrack": True,
            "cap_bind_general_max_saving_rate": (policy.get("cap_bind") or {}).get("general_max_saving_rate"),
            "headline_golden_core_only": True,
        },
        "explicit_hold": {
            "active_report_kpi_update": False,
            "ms_paste_hwpx_kpi_body": False,
        },
        "promote_candidate": str(PROMOTE_OUT.relative_to(ROOT)).replace("\\", "/"),
        "gates_passed": gates_ok,
    }
    SIGNOFF_APPEND.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": gates_ok, "out": str(PROMOTE_OUT), "logos_j": logos_j, "gc_j": gc_j}, ensure_ascii=False))
    return 0 if gates_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
