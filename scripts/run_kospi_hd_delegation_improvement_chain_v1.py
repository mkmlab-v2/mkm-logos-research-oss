#!/usr/bin/env python3
"""KOSPI B-track HD delegation improvement chain [HYPO][research_only].

Grid-search shadow → candidate compare → direction panel → significance.
Does not apply weights or promote Track A.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_hd_delegation_improvement_completion_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--as-of-kst", default="2026-06-26")
    ap.add_argument("--candidate-id", default="v2_bear_triple_align_boost")
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    steps = [
        _run(
            "parallel_shadow_bundle",
            [
                PY,
                "scripts/build_kospi_june2026_parallel_shadow_bundle_v1.py",
                "--year-month",
                ns.year_month,
                "--as-of-kst",
                ns.as_of_kst,
            ],
        ),
        _run(
            "cpcv_shadow_promotion_poc",
            [PY, "scripts/build_kospi_cpcv_shadow_promotion_poc_v1.py", "--as-of-kst", ns.as_of_kst],
        ),
        _run(
            "weight_candidate_compare",
            [PY, "scripts/run_kospi_june2026_weight_candidate_compare_v1.py", "--candidate-id", ns.candidate_id],
        ),
        _run(
            "direction_rule_shadow_panel",
            [
                PY,
                "scripts/build_kospi_direction_rule_shadow_panel_v1.py",
                "--year-month",
                ns.year_month,
                "--as-of-kst",
                ns.as_of_kst,
            ],
        ),
        _run(
            "oos_significance",
            [PY, "scripts/build_kospi_june2026_oos_significance_v1.py", "--year-month", ns.year_month],
        ),
    ]
    failed = [s for s in steps if s["exit_code"] != 0]
    if failed:
        print(json.dumps({"ok": False, "failed": [f["name"] for f in failed]}, ensure_ascii=False))
        return 1

    compare = json.loads(
        (ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json").read_text(encoding="utf-8-sig")
    )
    parallel = json.loads(
        (ROOT / "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    panel = json.loads(
        (ROOT / f"reports/kospi_{ns.year_month.replace('-', '')}_direction_rule_shadow_panel_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    sig = json.loads(
        (ROOT / "reports/kospi_june2026_oos_significance_v1_latest.json").read_text(encoding="utf-8-sig")
    )

    june = compare.get("june_forward_eval") or {}
    active_soft = float((june.get("active") or {}).get("metrics", {}).get("soft_hit_rate") or 0)
    cand_soft = float((june.get("candidate") or {}).get("metrics", {}).get("soft_hit_rate") or 0)
    delta_pp = round((cand_soft - active_soft) * 100, 2)

    bear_rule = next(
        (r for r in (panel.get("weight_rules") or []) if r.get("rule_id") == "bear_triple_align_boost_v2"),
        {},
    )

    parallel_leader = parallel.get("leader_arm") or {}
    parallel_delta = float((parallel.get("soft_delta_vs_active") or {}).get("composite_bear_conditional") or 0)
    cpcv_path = ROOT / "reports/kospi_cpcv_shadow_promotion_poc_v1_latest.json"
    cpcv = json.loads(cpcv_path.read_text(encoding="utf-8-sig")) if cpcv_path.is_file() else {}

    doc: dict[str, Any] = {
        "schema": "kospi_hd_delegation_improvement_completion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "mission_line": "KOSPI B-track HD delegation: bear_triple_align_boost_v2 shadow uplift",
        "candidate_id": ns.candidate_id,
        "year_month": ns.year_month,
        "quality_ok": (
            delta_pp >= 5.0
            or float(parallel_leader.get("soft_delta_pp") or 0) >= 5.0
            or (cpcv.get("promotion_poc_gate") or {}).get("pass") is True
        ),
        "june_forward": {
            "active_soft_hit_rate": active_soft,
            "candidate_soft_hit_rate": cand_soft,
            "soft_delta_pp": delta_pp,
            "n_direction_diffs": compare.get("n_direction_diffs"),
            "promotion_ready": (compare.get("promotion_recommendation") or {}).get("promotion_ready"),
        },
        "parallel_shadow_bundle": {
            "leader_arm": parallel_leader,
            "composite_soft_delta_pp": round(parallel_delta * 100, 2),
            "fail_rescue_soft_delta_pp": round(
                float((parallel.get("soft_delta_vs_active") or {}).get("fail_rescue_triple") or 0) * 100,
                2,
            ),
            "session_2026_06_26_composite_outcome": (
                (parallel.get("session_2026_06_26") or {}).get("arms", {}).get("composite_bear_conditional", {})
            ).get("outcome"),
            "lit_review": "docs/research/KOSPI_REGIME_SWITCH_CPCV_LIT_REVIEW_2026-06-26.md",
        },
        "cpcv_promotion_poc": {
            "pass": (cpcv.get("promotion_poc_gate") or {}).get("pass"),
            "verdict_ko": (cpcv.get("promotion_poc_gate") or {}).get("verdict_ko"),
            "median_soft_delta": (cpcv.get("fold_summary") or {}).get("median_soft_delta"),
            "positive_rate": (cpcv.get("fold_summary") or {}).get("positive_rate"),
            "artifact": "reports/kospi_cpcv_shadow_promotion_poc_v1_latest.json",
        },
        "direction_panel": {
            "bear_triple_rule_minus_active_soft_pp": bear_rule.get("rule_minus_active_soft_pp"),
            "n_rescued_active_fail": bear_rule.get("n_rescued_active_fail"),
            "verdict_ko": panel.get("verdict_ko"),
        },
        "scoring_shadow_significance": {
            "directional_hit_rate": (sig.get("raw_metrics") or {}).get("directional_hit_rate"),
            "wilson_verdict_ko": (sig.get("significance") or {}).get("directional", {}).get("verdict_ko"),
        },
        "steps": steps,
        "reproducible_command": (
            f"py scripts/run_kospi_hd_delegation_improvement_chain_v1.py "
            f"--candidate-id {ns.candidate_id} --year-month {ns.year_month} --as-of-kst {ns.as_of_kst}"
        ),
        "boundary_ack": "Shadow research only; active arm unchanged; Track A·apply forbidden.",
    }

    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "quality_ok": doc["quality_ok"], "delta_pp": delta_pp, "out": str(ns.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
