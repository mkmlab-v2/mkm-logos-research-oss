#!/usr/bin/env python3
"""Rebuild B-track compression bridge / cap evidence summary from disk artifacts (RQ-016).

Reads Track A active + B-track pinpoint/sweep JSON only. Never overwrites active report.
Writes ``docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
HEALTH_PIN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_HEALTH_BRIDGE_PINPOINT_V1.json"
SSOT_PIN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json"
LOW_SAVING_SWEEP = ROOT / "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json"
SSOT_MICROGRID = ROOT / "docs/final/artifacts/compression_ssot_relaxed_cap_microgrid_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json"
POLICY_FLOOR = 0.47
HEALTH_CASE = "cmp2_014"

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
    }
)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _case_j(report: dict[str, Any], case_id: str) -> float | None:
    for c in (report.get("compression_metrics") or {}).get("cases") or []:
        if str(c.get("id", "")) == case_id:
            v = c.get("reconstruction_fidelity_jaccard")
            return float(v) if v is not None else None
    return None


def _scm_min(report: dict[str, Any]) -> float | None:
    ids = {"cmp2_015", "cmp2_023", "cmp2_028"}
    vals = []
    for c in (report.get("compression_metrics") or {}).get("cases") or []:
        if str(c.get("id", "")) in ids:
            vals.append(float(c.get("reconstruction_fidelity_jaccard") or 0))
    return min(vals) if vals else None


def _global(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
    }


def _assert_safe_out(path: Path) -> Path:
    if path.resolve() in FORBIDDEN_WRITE:
        raise SystemExit(f"Refusing to write Track A active: {path}")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = _assert_safe_out(args.out_json)

    ta = _load(TRACK_A_ACTIVE)
    if ta is None:
        raise SystemExit(f"Missing Track A reference (read-only): {TRACK_A_ACTIVE}")

    tacm = ta.get("compression_metrics") or {}
    track_a_frozen = {
        "path": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "apply_gematria_4d_bridge_policy": (ta.get("run_config") or {}).get(
            "apply_gematria_4d_bridge_policy"
        ),
        **_global(ta),
        "scm_min_jaccard": _scm_min(ta),
        "health_jaccard": _case_j(ta, HEALTH_CASE),
    }

    health_pin_doc = _load(HEALTH_PIN)
    ssot_pin_doc = _load(SSOT_PIN)
    sweep_doc = _load(LOW_SAVING_SWEEP)
    ssot_micro = _load(SSOT_MICROGRID)

    health_winner: dict[str, Any] | None = None
    if health_pin_doc:
        env = health_pin_doc.get("b_track_envelope") or {}
        pm = env.get("pinpoint_metrics") or {}
        hc = pm.get("health_case") or {}
        health_winner = {
            "id": "health_bridge_saving_heavy",
            "regenerate_script": "scripts/run_ultra_compression_health_bridge_pinpoint_v1.py",
            "artifact_pinpoint": str(HEALTH_PIN.relative_to(ROOT)).replace("\\", "/"),
            "bridge_policy_domain_allowlist": (env.get("pin_config") or {}).get(
                "bridge_policy_domain_allowlist"
            ),
            "bridge_score_weights": (env.get("pin_config") or {}).get("bridge_score_weights"),
            "global_token_saving_rate": pm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": pm.get("avg_reconstruction_fidelity_jaccard"),
            "health_jaccard": hc.get("jaccard"),
            "scm_min_jaccard": _scm_min(health_pin_doc),
            "ultra_saving_policy_ok": pm.get("ultra_saving_policy_ok"),
        }
        if track_a_frozen.get("global_token_saving_rate") is not None:
            health_winner["delta_saving_vs_track_a"] = round(
                float(pm.get("global_token_saving_rate") or 0)
                - float(track_a_frozen["global_token_saving_rate"]),
                6,
            )
            health_winner["delta_avg_jaccard_vs_track_a"] = round(
                float(pm.get("avg_reconstruction_fidelity_jaccard") or 0)
                - float(track_a_frozen["avg_reconstruction_fidelity_jaccard"] or 0),
                6,
            )

    ssot_a_plan: dict[str, Any] | None = None
    if ssot_pin_doc:
        env = ssot_pin_doc.get("b_track_envelope") or {}
        pm = env.get("pinpoint_metrics") or {}
        gates = env.get("promotion_gates") or {}
        ssot_a_plan = {
            "id": "ssot_relaxed_cap_0.45",
            "regenerate_script": "scripts/run_ultra_compression_ssot_relaxed_cap_pinpoint_v1.py",
            "artifact_pinpoint": str(SSOT_PIN.relative_to(ROOT)).replace("\\", "/"),
            "pin_config": env.get("pin_config"),
            **pm,
            "promotion_gates": gates,
            "ssot_domain_diff_summary": env.get("ssot_domain_diff_summary"),
            "top5_low_saving_diff_summary": env.get("top5_low_saving_diff_summary"),
            "worst_jaccard_case": env.get("worst_jaccard_case"),
            "jaccard_regression_case_ids": [
                r["id"]
                for r in (env.get("by_id_diff_vs_track_a") or [])
                if (r.get("delta_jaccard") or 0) < -1e-9
            ],
        }
        if track_a_frozen.get("global_token_saving_rate") is not None:
            ssot_a_plan["delta_saving_vs_track_a"] = pm.get("delta_global_saving_vs_track_a")

    ssot_microgrid: dict[str, Any] | None = None
    if ssot_micro:
        ssot_microgrid = {
            "regenerate_script": "scripts/run_compression_ssot_relaxed_cap_microgrid_v1.py",
            "artifact": str(SSOT_MICROGRID.relative_to(ROOT)).replace("\\", "/"),
            "joint_floor_and_min_j_pass_count": ssot_micro.get("joint_floor_and_min_j_pass_count"),
            "key_finding": ssot_micro.get("key_finding"),
            "best_by_rank": ssot_micro.get("best_by_rank"),
        }

    low_saving_sweep: dict[str, Any] | None = None
    if sweep_doc:
        best = sweep_doc.get("best_by_floor_then_saving") or {}
        low_saving_sweep = {
            "regenerate_script": "scripts/run_compression_low_saving_local_cap_sweep_v1.py",
            "artifact": str(LOW_SAVING_SWEEP.relative_to(ROOT)).replace("\\", "/"),
            "variant_count": sweep_doc.get("variant_count"),
            "floor_pass_count": sweep_doc.get("floor_pass_count"),
            "best_variant_id": best.get("id"),
            "best_global_saving_rate": best.get("global_token_saving_rate"),
            "audit_note": (sweep_doc.get("audit") or {}).get("note"),
        }

    comparison_rows = [
        {
            "variant": "track_a_active_frozen",
            "saving_pct": round(float(track_a_frozen["global_token_saving_rate"]) * 100, 2),
            "avg_jaccard": round(float(track_a_frozen["avg_reconstruction_fidelity_jaccard"]), 3),
            "scm_min": track_a_frozen.get("scm_min_jaccard"),
            "health_jaccard": track_a_frozen.get("health_jaccard"),
            "floor_ok": track_a_frozen.get("ultra_saving_policy_ok"),
        },
    ]
    if health_winner:
        comparison_rows.append(
            {
                "variant": "health_bridge_saving_heavy",
                "saving_pct": round(float(health_winner["global_token_saving_rate"]) * 100, 2),
                "avg_jaccard": round(float(health_winner["avg_reconstruction_fidelity_jaccard"]), 3),
                "scm_min": health_winner.get("scm_min_jaccard"),
                "health_jaccard": health_winner.get("health_jaccard"),
                "floor_ok": health_winner.get("ultra_saving_policy_ok"),
            }
        )
    if ssot_a_plan:
        comparison_rows.append(
            {
                "variant": "ssot_relaxed_cap_0.45",
                "saving_pct": round(float(ssot_a_plan["global_token_saving_rate"]) * 100, 2),
                "avg_jaccard": round(float(ssot_a_plan["avg_reconstruction_fidelity_jaccard"]), 3),
                "min_jaccard": ssot_a_plan.get("min_reconstruction_fidelity_jaccard"),
                "floor_ok": ssot_a_plan.get("ultra_saving_policy_ok"),
                "auto_track_a_promotion_allowed": (ssot_a_plan.get("promotion_gates") or {}).get(
                    "auto_track_a_promotion_allowed"
                ),
            }
        )

    floor_pass_ssot = bool(ssot_a_plan and ssot_a_plan.get("ultra_saving_policy_ok"))
    min_j_ok = bool(
        ssot_a_plan
        and (ssot_a_plan.get("promotion_gates") or {}).get("min_jaccard_not_below_track_a")
    )
    if floor_pass_ssot and not min_j_ok:
        recommendation = (
            "freeze_track_a_baseline; b_track_ssot_relaxed_cap_0.45_passes_floor_but_min_j_regresses; "
            "human_review_before_track_a; health_pin_case_only_not_global"
        )
    elif floor_pass_ssot and min_j_ok:
        recommendation = "human_review_ssot_pin_candidate_for_track_a"
    else:
        recommendation = (
            "freeze_track_a_keep_baseline; b_track_health_pin_for_health_case_only; "
            "no_track_a_promotion_without_human_and_floor_pass"
        )

    evidence_refs = [
        "docs/final/artifacts/compression_domain_bridge_sweep_v1_latest.json",
        "docs/final/artifacts/compression_scm_cap_tune_sweep_v1_latest.json",
        "docs/final/artifacts/compression_scm_bridge_weight_grid_v2_latest.json",
        str(HEALTH_PIN.relative_to(ROOT)).replace("\\", "/"),
        "docs/final/artifacts/compression_health_bridge_floor_microgrid_v1_latest.json",
        str(SSOT_PIN.relative_to(ROOT)).replace("\\", "/"),
        str(LOW_SAVING_SWEEP.relative_to(ROOT)).replace("\\", "/"),
        str(SSOT_MICROGRID.relative_to(ROOT)).replace("\\", "/"),
    ]

    doc = {
        "schema": "compression_b_track_bridge_evidence_summary_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": POLICY_FLOOR,
        "track_a_frozen": track_a_frozen,
        "b_track_health_pin_winner": health_winner,
        "b_track_ssot_relaxed_cap_a_plan": ssot_a_plan,
        "low_saving_local_cap_sweep": low_saving_sweep,
        "ssot_relaxed_cap_microgrid": ssot_microgrid,
        "scm_bridge_outcome": {
            "scm_min_jaccard_achieved": 1.0,
            "global_token_saving_rate_typical": 0.3938115330520394,
            "joint_floor_and_scm_pareto": False,
            "recommendation": "scm_only_not_viable_for_track_a_floor",
        },
        "comparison_rows": comparison_rows,
        "health_floor_microgrid": {
            "regenerate_script": "scripts/run_compression_health_bridge_floor_microgrid_v1.py",
            "artifact": "docs/final/artifacts/compression_health_bridge_floor_microgrid_v1_latest.json",
            "key_finding": "no joint floor_pass and health_jaccard=1.0",
        },
        "evidence_refs": evidence_refs,
        "recommendation": recommendation,
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "recommendation": recommendation}, ensure_ascii=False, indent=2))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "recommendation": recommendation,
                "ssot_floor_ok": floor_pass_ssot,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
