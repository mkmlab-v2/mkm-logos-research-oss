#!/usr/bin/env python3
"""[HYPO] Conditional fusion ablation — P(codec|shard,recon_error,corpus) vs linear blend.

Compares:
  - baseline_active (Golden-40 per-case disk metrics)
  - linear_blend_wrong (forbidden scalar α·β·γ mix — negative control)
  - conditional_fusion_v1 (shard/error/confidence routing proxy)
  - corpus_hybrid_routed (hybrid spike operational metrics)

Uses existing manifests only — no ACTIVE write, no live codec rerun.
research_only · send_gate HOLD · apply_forbidden.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROUTING_MANIFEST = ROOT / "reports/compression_routing_confidence_ng40_manifest_v1_latest.json"
KNEE_SUMMARY = ROOT / "reports/ng40_path_b_knee_summary_v1_latest.json"
HYBRID_SPIKE = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
SOTA_ABLATION = ROOT / "reports/compression_sota_ablation_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_conditional_fusion_ablation_v1_latest.json"
SCHEMA = "compression_conditional_fusion_ablation_v1"

SSOT_SHARD = "zone_d_ssot"
RECON_ERR_GUARD = 0.15
REL_CONF_GUARD = 0.95
HIGH_CONF = 0.92

KNEE_J_SAVING = 0.4317862165963432
KNEE_J_JACCARD = 0.9114604549647121
LLMLINGUA_G40_SAVING = 0.5111987122784335
LLMLINGUA_G40_JACCARD = 0.4756325662856236


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _min_j(rows: list[dict[str, Any]]) -> float | None:
    vals = [float(r["reconstruction_fidelity_jaccard"]) for r in rows if "reconstruction_fidelity_jaccard" in r]
    return min(vals) if vals else None


def _holdout_split(case_ids: list[str], holdout_frac: float) -> tuple[set[str], set[str]]:
    scored = sorted(
        ((cid, int(hashlib.sha256(cid.encode()).hexdigest()[:8], 16)) for cid in case_ids),
        key=lambda x: x[1],
    )
    n_hold = max(1, int(round(len(scored) * holdout_frac)))
    holdout = {cid for cid, _ in scored[:n_hold]}
    train = {cid for cid, _ in scored[n_hold:]}
    return train, holdout


def pick_policy(case: dict[str, Any]) -> str:
    err = float(case.get("reconstruction_error") or 0.0)
    shard = str(case.get("shard_id") or "")
    rel = float(case.get("shard_relative_confidence") or 1.0)
    conf = float(case.get("router_confidence") or 0.0)
    if shard == SSOT_SHARD and (err >= RECON_ERR_GUARD or rel < REL_CONF_GUARD):
        return "knee_j_guard"
    if err >= 0.20:
        return "knee_j_guard"
    if conf >= HIGH_CONF:
        return "latent_active"
    return "latent_default"


def pick_policy_ssot_only(case: dict[str, Any]) -> str:
    """SSOT shard bleed only — no global recon_error guard (v3 recommended)."""
    err = float(case.get("reconstruction_error") or 0.0)
    shard = str(case.get("shard_id") or "")
    rel = float(case.get("shard_relative_confidence") or 1.0)
    if shard == SSOT_SHARD and (err >= RECON_ERR_GUARD or rel < REL_CONF_GUARD):
        return "knee_j_guard"
    return "latent_active"


def apply_knee_j_guard_proxy(saving: float, jaccard: float, err: float) -> tuple[float, float]:
    blend = min(1.0, err / 0.25)
    new_s = saving * (1.0 - blend * 0.12)
    new_j = min(1.0, jaccard + blend * max(0.0, KNEE_J_JACCARD - jaccard) * 0.4)
    return round(new_s, 6), round(new_j, 6)


def case_rows_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in manifest.get("per_case") or []:
        if not isinstance(case, dict):
            continue
        saving = float(case.get("token_saving_rate") or 0.0)
        j = float(case.get("reconstruction_fidelity_jaccard") or 0.0)
        rows.append(
            {
                "id": str(case.get("id") or ""),
                "shard_id": str(case.get("shard_id") or ""),
                "domain": str(case.get("domain") or ""),
                "reconstruction_error": float(case.get("reconstruction_error") or 0.0),
                "router_confidence": float(case.get("router_confidence") or 0.0),
                "shard_relative_confidence": float(case.get("shard_relative_confidence") or 1.0),
                "baseline_saving": saving,
                "baseline_jaccard": j,
            }
        )
    return rows


def _policy_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        p = str(r.get("policy") or "unknown")
        counts[p] = counts.get(p, 0) + 1
    return counts


def arm_metrics(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        s0 = row["baseline_saving"]
        j0 = row["baseline_jaccard"]
        err = row["reconstruction_error"]
        if arm == "baseline_active":
            s, j = s0, j0
            policy = "active_disk"
        elif arm == "linear_blend_wrong":
            s = 0.4 * s0 + 0.35 * KNEE_J_SAVING + 0.25 * LLMLINGUA_G40_SAVING
            j = 0.4 * j0 + 0.35 * KNEE_J_JACCARD + 0.25 * LLMLINGUA_G40_JACCARD
            policy = "linear_forbidden"
        elif arm == "conditional_fusion_v1":
            policy = pick_policy(row)
            if policy == "knee_j_guard":
                s, j = apply_knee_j_guard_proxy(s0, j0, err)
            else:
                s, j = s0, j0
        else:
            raise ValueError(f"unknown arm: {arm}")
        out_rows.append(
            {
                **row,
                "arm": arm,
                "policy": policy,
                "token_saving_rate": round(s, 6),
                "reconstruction_fidelity_jaccard": round(j, 6),
            }
        )
    return {
        "arm": arm,
        "case_count": len(out_rows),
        "mean_token_saving_rate": round(_mean(out_rows, "token_saving_rate") or 0.0, 6),
        "mean_jaccard": round(_mean(out_rows, "reconstruction_fidelity_jaccard") or 0.0, 6),
        "min_jaccard": round(_min_j(out_rows) or 0.0, 6),
        "policy_counts": _policy_counts(out_rows),
        "rows": out_rows,
    }


def _delta_vs_baseline(baseline: dict[str, Any], arm: dict[str, Any]) -> dict[str, float | None]:
    return {
        "mean_saving_delta": round(
            float(arm["mean_token_saving_rate"]) - float(baseline["mean_token_saving_rate"]), 6
        ),
        "mean_jaccard_delta": round(float(arm["mean_jaccard"]) - float(baseline["mean_jaccard"]), 6),
        "min_jaccard_delta": round(float(arm["min_jaccard"]) - float(baseline["min_jaccard"]), 6),
    }


def corpus_tier_ablation(hybrid: dict[str, Any] | None, sota: dict[str, Any] | None) -> dict[str, Any]:
    if not hybrid:
        return {"present": False}
    cmp_block = hybrid.get("comparison") or {}
    hybrid_op = cmp_block.get("operational_post_jaccard_floor") or cmp_block.get("hybrid_routed") or {}
    all_mkm = (cmp_block.get("baselines_from_ablation") or {}).get("all_mkm_economy_from_ablation") or {}
    all_llm = (cmp_block.get("baselines_from_ablation") or {}).get("all_llmlingua2_from_ablation") or {}
    corpora: list[dict[str, Any]] = []
    for corp in hybrid.get("corpora") or []:
        if not isinstance(corp, dict):
            continue
        route = corp.get("route") or {}
        res = corp.get("result") or {}
        op = res.get("operational_post_jaccard_floor") or res.get("raw") or {}
        corpora.append(
            {
                "corpus_id": corp.get("corpus_id"),
                "backend": route.get("backend"),
                "route_reason": route.get("reason"),
                "mean_saving": op.get("mean_token_saving_rate_proxy"),
                "mean_jaccard": op.get("mean_jaccard_proxy"),
                "rows": op.get("rows"),
            }
        )
    return {
        "present": True,
        "tier_a_gate": hybrid.get("tier_a_gate"),
        "corpus_routes": corpora,
        "aggregate": {
            "all_mkm_raw": all_mkm,
            "all_llmlingua2_raw": all_llm,
            "hybrid_routed_operational": hybrid_op,
            "delta_hybrid_minus_all_mkm_saving": cmp_block.get("delta_hybrid_minus_all_mkm_raw_saving"),
            "delta_hybrid_minus_all_mkm_jaccard": cmp_block.get("delta_hybrid_minus_all_mkm_raw_jaccard"),
        },
        "sota_ablation_present": bool(sota),
        "note_ko": "corpus-conditional route — global headline merge 금지",
    }


def build(*, holdout_frac: float) -> dict[str, Any]:
    manifest = _load(ROUTING_MANIFEST)
    if not manifest:
        raise FileNotFoundError(f"missing routing manifest: {ROUTING_MANIFEST}")
    knee = _load(KNEE_SUMMARY) or {}
    hybrid = _load(HYBRID_SPIKE)
    sota = _load(SOTA_ABLATION)

    base_rows = case_rows_from_manifest(manifest)
    if len(base_rows) != 40:
        raise ValueError(f"expected 40 cases, got {len(base_rows)}")

    train_ids, holdout_ids = _holdout_split([r["id"] for r in base_rows], holdout_frac)
    holdout_rows = [r for r in base_rows if r["id"] in holdout_ids]

    arms_full: dict[str, Any] = {}
    for arm in ("baseline_active", "linear_blend_wrong", "conditional_fusion_v1"):
        arms_full[arm] = arm_metrics(base_rows, arm)

    baseline_full = arms_full["baseline_active"]
    compare_full = {
        arm: _delta_vs_baseline(baseline_full, arms_full[arm])
        for arm in ("linear_blend_wrong", "conditional_fusion_v1")
    }

    arms_holdout: dict[str, Any] = {}
    for arm in ("baseline_active", "linear_blend_wrong", "conditional_fusion_v1"):
        arms_holdout[arm] = {k: v for k, v in arm_metrics(holdout_rows, arm).items() if k != "rows"}

    baseline_hold = arms_holdout["baseline_active"]
    compare_holdout = {
        arm: _delta_vs_baseline(baseline_hold, arms_holdout[arm])
        for arm in ("linear_blend_wrong", "conditional_fusion_v1")
    }

    cf_hold = compare_holdout["conditional_fusion_v1"]
    verdict_ko = [
        "linear_blend_wrong = forbidden negative control (scalar KPI merge)",
        f"conditional_fusion holdout min_j delta {cf_hold.get('min_jaccard_delta')} pp",
        f"conditional_fusion holdout mean_j delta {cf_hold.get('mean_jaccard_delta')} pp",
        "proxy counterfactual — real codec rerun ablation still required for promotion",
        "apply_active · Track A headline merge 금지",
    ]
    uplift_signal = (
        cf_hold.get("min_jaccard_delta") is not None
        and float(cf_hold["min_jaccard_delta"]) > 0
        and cf_hold.get("mean_jaccard_delta") is not None
        and float(cf_hold["mean_jaccard_delta"]) >= -0.005
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_forbidden": True,
        "theory_lane": "compression_conditional_fusion",
        "protocol": {
            "model": "P(codec | shard, recon_error, shard_relative_confidence, corpus_tier)",
            "negative_control": "linear_blend_wrong",
            "holdout_frac": holdout_frac,
            "holdout_case_ids": sorted(holdout_ids),
            "train_case_count": len(train_ids),
            "holdout_case_count": len(holdout_ids),
            "proxy_only": True,
            "note_ko": "Golden-40 case metrics + policy counterfactual — not ACTIVE rewrite",
        },
        "policy_thresholds": {
            "ssot_shard": SSOT_SHARD,
            "recon_err_guard": RECON_ERR_GUARD,
            "rel_conf_guard": REL_CONF_GUARD,
            "high_confidence": HIGH_CONF,
        },
        "pointers": {
            "routing_manifest": str(ROUTING_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "knee_summary": str(KNEE_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_spike": str(HYBRID_SPIKE.relative_to(ROOT)).replace("\\", "/"),
            "topology_sidecar": (
                "docs/final/artifacts/logos_topology_sidecar_compression_improvement_multilens_v1_latest.json"
            ),
        },
        "frozen_active_headline": manifest.get("frozen_active_headline") or {},
        "knee_j_first_reference": knee.get("knee_j_first"),
        "golden40_arms_full": {arm: {k: v for k, v in arms_full[arm].items() if k != "rows"} for arm in arms_full},
        "golden40_compare_full": compare_full,
        "golden40_arms_holdout": arms_holdout,
        "golden40_compare_holdout": compare_holdout,
        "corpus_tier": corpus_tier_ablation(hybrid, sota),
        "uplift_signal_holdout": uplift_signal,
        "verdict_ko": verdict_ko,
        "forbidden": [
            "merge conditional proxy with ACTIVE 47% headline",
            "linear_blend_wrong as product KPI",
            "apply_active without real codec beat_frozen",
        ],
        "reproducible_command": (
            f"py scripts/run_compression_conditional_fusion_ablation_v1.py --holdout-frac {holdout_frac}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--holdout-frac", type=float, default=0.2)
    ap.add_argument("--write-sample-rows", action="store_true")
    args = ap.parse_args()

    doc = build(holdout_frac=args.holdout_frac)
    if args.write_sample_rows:
        manifest = _load(ROUTING_MANIFEST)
        if manifest:
            base_rows = case_rows_from_manifest(manifest)
            doc["golden40_sample_rows"] = arm_metrics(base_rows, "conditional_fusion_v1")["rows"][:8]

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "uplift_signal_holdout": doc["uplift_signal_holdout"],
                "cf_min_j_delta": doc["golden40_compare_holdout"]["conditional_fusion_v1"]["min_jaccard_delta"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
