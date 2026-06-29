#!/usr/bin/env python3
"""[HYPO] Wire v3 SSOT-only conditional fusion into hybrid router spike (golden40_internal).

Replaces golden40 llmlingua2 regress route with mkm_conditional_fusion_v3_ssot_guard
using real evaluate_report codec merge (v3 ablation SSOT).
research_only · send_gate HOLD · no ACTIVE mutation.
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

from scripts.run_compression_conditional_fusion_ablation_v1 import (  # noqa: E402
    ROUTING_MANIFEST,
    case_rows_from_manifest,
    pick_policy_ssot_only,
)
from scripts.run_compression_conditional_fusion_ablation_v2_codec_rerun_v1 import (  # noqa: E402
    _aggregate_cases,
    _case_index,
    _delta_vs,
    _load,
    ACTIVE_REPORT_OUT,
    KNEE_J_REPORT_OUT,
)
from scripts.run_compression_hybrid_router_spike_v1 import (  # noqa: E402
    DEFAULT_ABLATION,
    TIER_A_GATE_CORPORA,
    TIER_A_EXCLUDE_CORPUS,
    _baseline_from_ablation,
    _mean,
)

BASE_SPIKE = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
V3_ABLATION = ROOT / "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_hybrid_router_v3_wire_spike_v1_latest.json"
GOLDEN40_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
SCHEMA = "compression_hybrid_router_v3_wire_spike_v1"
JACCARD_FLOOR = 0.73


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _merge_golden40_cases() -> tuple[list[dict[str, Any]], dict[str, int]]:
    manifest = _load(ROUTING_MANIFEST)
    if not manifest:
        raise FileNotFoundError(f"missing routing manifest: {ROUTING_MANIFEST}")
    active_report = _load(ACTIVE_REPORT_OUT)
    knee_report = _load(KNEE_J_REPORT_OUT)
    if not active_report or not knee_report:
        raise FileNotFoundError("missing v2 codec caches — run v2 ablation first")
    active_idx = _case_index(active_report)
    knee_idx = _case_index(knee_report)
    routing_rows = case_rows_from_manifest(manifest)
    merged: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in routing_rows:
        cid = row["id"]
        policy = pick_policy_ssot_only(row)
        counts[policy] = counts.get(policy, 0) + 1
        src = knee_idx if policy == "knee_j_guard" else active_idx
        case = src[cid]
        j = float(case.get("reconstruction_fidelity_jaccard") or 0.0)
        s = float(case.get("token_saving_rate") or 0.0)
        merged.append(
            {
                "id": cid,
                "ok": j >= JACCARD_FLOOR,
                "policy": policy,
                "source_arm": "knee_j_codec" if policy == "knee_j_guard" else "active_codec",
                "shard_id": row.get("shard_id"),
                "token_saving_rate_proxy": round(s, 6),
                "jaccard_proxy": round(j, 6),
                "reconstruction_fidelity_jaccard": round(j, 6),
                "token_saving_rate": round(s, 6),
            }
        )
    return merged, counts


def _golden40_result_block(merged: list[dict[str, Any]]) -> dict[str, Any]:
    savings = [float(r["token_saving_rate_proxy"]) for r in merged]
    jaccards = [float(r["jaccard_proxy"]) for r in merged]
    op_savings = [float(r["token_saving_rate_proxy"]) for r in merged if r.get("ok")]
    op_jaccards = [float(r["jaccard_proxy"]) for r in merged if r.get("ok")]
    failures = sum(1 for r in merged if not r.get("ok"))
    return {
        "backend": "mkm_conditional_fusion_v3_ssot_guard",
        "family": "mkm_evaluate_report_conditional_merge",
        "compression_profile": "active_with_ssot_knee_j_guard",
        "rows": len(merged),
        "rows_ok": sum(1 for r in merged if r.get("ok")),
        "failures": failures,
        "raw": {
            "mean_token_saving_rate_proxy": _mean(savings),
            "mean_jaccard_proxy": _mean(jaccards),
            "rows": len(savings),
        },
        "operational_post_jaccard_floor": {
            "mean_token_saving_rate_proxy": _mean(op_savings),
            "mean_jaccard_proxy": _mean(op_jaccards),
            "rows": len(op_savings),
            "jaccard_floor": JACCARD_FLOOR,
        },
        "row_samples": merged[:3],
        "per_case_policy_count": len(merged),
    }


def _recompute_hybrid_comparison(corpora: list[dict[str, Any]], ablation: dict[str, Any]) -> dict[str, Any]:
    hybrid_savings: list[float] = []
    hybrid_jaccards: list[float] = []
    hybrid_op_savings: list[float] = []
    hybrid_op_jaccards: list[float] = []
    for cr in corpora:
        result = cr.get("result") or {}
        raw = result.get("raw") or {}
        op = result.get("operational_post_jaccard_floor") or {}
        if isinstance(raw.get("mean_token_saving_rate_proxy"), (int, float)):
            hybrid_savings.append(float(raw["mean_token_saving_rate_proxy"]))
        if isinstance(raw.get("mean_jaccard_proxy"), (int, float)):
            hybrid_jaccards.append(float(raw["mean_jaccard_proxy"]))
        if isinstance(op.get("mean_token_saving_rate_proxy"), (int, float)):
            hybrid_op_savings.append(float(op["mean_token_saving_rate_proxy"]))
        if isinstance(op.get("mean_jaccard_proxy"), (int, float)):
            hybrid_op_jaccards.append(float(op["mean_jaccard_proxy"]))
    baselines = _baseline_from_ablation(ablation)
    hybrid_raw_s = _mean(hybrid_savings)
    hybrid_raw_j = _mean(hybrid_jaccards)
    all_mkm_s = baselines["all_mkm_economy_from_ablation"]["mean_token_saving_rate_proxy"]
    all_llm_s = baselines["all_llmlingua2_from_ablation"]["mean_token_saving_rate_proxy"]
    all_mkm_j = baselines["all_mkm_economy_from_ablation"]["mean_jaccard_proxy"]
    all_llm_j = baselines["all_llmlingua2_from_ablation"]["mean_jaccard_proxy"]
    return {
        "baselines_from_ablation": baselines,
        "hybrid_routed": {
            "raw": {
                "mean_token_saving_rate_proxy": hybrid_raw_s,
                "mean_jaccard_proxy": hybrid_raw_j,
                "corpus_count": len(hybrid_savings),
            },
            "operational_post_jaccard_floor": {
                "mean_token_saving_rate_proxy": _mean(hybrid_op_savings),
                "mean_jaccard_proxy": _mean(hybrid_op_jaccards),
                "corpus_count": len(hybrid_op_savings),
            },
        },
        "delta_hybrid_minus_all_mkm_raw_saving": (
            hybrid_raw_s - all_mkm_s
            if isinstance(hybrid_raw_s, (int, float)) and isinstance(all_mkm_s, (int, float))
            else None
        ),
        "delta_hybrid_minus_all_llm_raw_saving": (
            hybrid_raw_s - all_llm_s
            if isinstance(hybrid_raw_s, (int, float)) and isinstance(all_llm_s, (int, float))
            else None
        ),
        "delta_hybrid_minus_all_mkm_raw_jaccard": (
            hybrid_raw_j - all_mkm_j
            if isinstance(hybrid_raw_j, (int, float)) and isinstance(all_mkm_j, (int, float))
            else None
        ),
    }


def build(*, base_spike_path: Path, ablation_path: Path) -> dict[str, Any]:
    base = _load(base_spike_path)
    if not base:
        raise FileNotFoundError(f"missing base spike: {base_spike_path}")
    ablation = _load(ablation_path)
    if not ablation:
        raise FileNotFoundError(f"missing ablation: {ablation_path}")
    v3 = _load(V3_ABLATION) or {}

    merged_cases, policy_counts = _merge_golden40_cases()
    active_idx = _case_index(_load(ACTIVE_REPORT_OUT) or {})
    knee_idx = _case_index(_load(KNEE_J_REPORT_OUT) or {})
    manifest_rows = case_rows_from_manifest(_load(ROUTING_MANIFEST) or {})
    row_by_id = {r["id"]: r for r in manifest_rows}
    for i, row in enumerate(merged_cases):
        pol = pick_policy_ssot_only(row_by_id[row["id"]])
        src = knee_idx if pol == "knee_j_guard" else active_idx
        case = src[row["id"]]
        merged_cases[i]["raw_tokens"] = case.get("raw_tokens")
        merged_cases[i]["compressed_tokens"] = case.get("compressed_tokens")
        merged_cases[i]["reconstruction_fidelity_jaccard"] = case.get("reconstruction_fidelity_jaccard")

    g40_result = _golden40_result_block(merged_cases)
    g40_agg = _aggregate_cases(merged_cases)

    new_route = {
        "corpus_id": "golden40_internal",
        "backend": "mkm_conditional_fusion_v3_ssot_guard",
        "reason": "v3 SSOT-only conditional fusion — replaces llmlingua2 regress lane",
        "override": True,
        "conditional_fusion_pointer": str(V3_ABLATION.relative_to(ROOT)).replace("\\", "/"),
        "policy": "pick_policy_ssot_only",
        "knee_j_guard_count": policy_counts.get("knee_j_guard", 0),
    }

    corpora_out: list[dict[str, Any]] = []
    routes_out: list[dict[str, Any]] = []
    for corp in base.get("corpora") or []:
        cid = corp.get("corpus_id")
        if cid == "golden40_internal":
            row_count = len(merged_cases)
            if GOLDEN40_INPUT.is_file():
                inp = _load(GOLDEN40_INPUT) or {}
                row_count = len(inp.get("compression_cases") or merged_cases)
            corpora_out.append(
                {
                    "corpus_id": "golden40_internal",
                    "label": corp.get("label") or "Golden-40 internal eval input (40 cases)",
                    "row_count": row_count,
                    "route": new_route,
                    "result": g40_result,
                    "v3_wire": {
                        "aggregate_evaluate_report": g40_agg,
                        "policy_counts": policy_counts,
                        "v3_ablation_pointer": str(V3_ABLATION.relative_to(ROOT)).replace("\\", "/"),
                    },
                }
            )
            routes_out.append(new_route)
        else:
            corpora_out.append(corp)
            routes_out.append((corp.get("route") or {}))

    old_g40 = next((c for c in base.get("corpora") or [] if c.get("corpus_id") == "golden40_internal"), {})
    old_result = old_g40.get("result") or {}
    old_raw = old_result.get("raw") or {}
    wire_delta = _delta_vs(
        {
            "global_token_saving_rate": float(old_raw.get("mean_token_saving_rate_proxy") or 0),
            "avg_reconstruction_fidelity_jaccard": float(old_raw.get("mean_jaccard_proxy") or 0),
            "min_reconstruction_fidelity_jaccard": 0.0,
        },
        g40_agg,
    )

    comparison = _recompute_hybrid_comparison(corpora_out, ablation)
    tier_a_pass_rates: list[float] = []
    for cr in corpora_out:
        cid = cr.get("corpus_id")
        if cid not in TIER_A_GATE_CORPORA:
            continue
        op = ((cr.get("result") or {}).get("operational_post_jaccard_floor") or {})
        rows_ok = op.get("rows")
        total = (cr.get("result") or {}).get("rows")
        if isinstance(rows_ok, int) and isinstance(total, int) and total > 0:
            tier_a_pass_rates.append(rows_ok / total)

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "labels": ["HYPO", "research_only", "B-track"],
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "apply_forbidden": True,
        "boundary_ack": (
            "golden40_internal wired to v3 SSOT conditional fusion (evaluate_report); "
            "not Track A ACTIVE promotion."
        ),
        "source_artifacts": {
            "base_hybrid_spike": str(base_spike_path.relative_to(ROOT)).replace("\\", "/"),
            "v3_ablation": str(V3_ABLATION.relative_to(ROOT)).replace("\\", "/"),
            "routing_manifest": str(ROUTING_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "sota_ablation": str(ablation_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "routing_policy": {
            **(base.get("routing_policy") or {}),
            "v3_wire": True,
            "golden40_backend_before": "llmlingua2",
            "golden40_backend_after": "mkm_conditional_fusion_v3_ssot_guard",
            "routes": routes_out,
        },
        "tier_a_gate": {
            "corpus_ids": sorted(TIER_A_GATE_CORPORA),
            "excluded_artifact_corpus": TIER_A_EXCLUDE_CORPUS,
            "mean_operational_pass_rate": _mean(tier_a_pass_rates),
            "jaccard_floor": JACCARD_FLOOR,
        },
        "corpora": corpora_out,
        "comparison": comparison,
        "golden40_wire_delta": wire_delta,
        "v3_conditional_headline": (v3.get("golden40_codec_arms") or {}).get("conditional_merged"),
        "sku_note": (
            "golden40 uses v3 conditional merge (real codec) — hybrid Jaccard up vs llmlingua regress lane."
        ),
        "reproducible_command": "py scripts/run_compression_hybrid_router_v3_wire_spike_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-spike", type=Path, default=BASE_SPIKE)
    ap.add_argument("--ablation-json", type=Path, default=DEFAULT_ABLATION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build(
        base_spike_path=args.base_spike if args.base_spike.is_absolute() else ROOT / args.base_spike,
        ablation_path=args.ablation_json if args.ablation_json.is_absolute() else ROOT / args.ablation_json,
    )
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    g40 = next(c for c in doc["corpora"] if c["corpus_id"] == "golden40_internal")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "golden40_backend": g40["route"]["backend"],
                "golden40_j": (g40["result"]["raw"] or {}).get("mean_jaccard_proxy"),
                "hybrid_j": doc["comparison"]["hybrid_routed"]["raw"]["mean_jaccard_proxy"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
