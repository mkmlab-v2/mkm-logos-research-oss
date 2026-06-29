#!/usr/bin/env python3
"""[HYPO] Conditional fusion ablation v2 — real evaluate_report codec rerun + policy merge.

Runs two Golden-40 codec arms (ACTIVE caps vs knee_j_first caps), merges per-case by
P(codec|shard,recon_error,rel_confidence) from routing manifest, compares to proxy v1.

No ACTIVE write · send_gate HOLD · apply_forbidden.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_compression_conditional_fusion_ablation_v1 import (  # noqa: E402
    ROUTING_MANIFEST,
    _holdout_split,
    case_rows_from_manifest,
    pick_policy,
)
from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    BASELINE_V2,
    INPUT_V2,
    _beat,
    _frozen_active,
    evaluate_ng40_lane,
)

PROXY_V1 = ROOT / "reports/compression_conditional_fusion_ablation_v1_latest.json"
KNEE_SUMMARY = ROOT / "reports/ng40_path_b_knee_summary_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json"
ACTIVE_REPORT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_conditional_fusion_active_arm_v1_latest.report.json"
)
KNEE_J_REPORT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_conditional_fusion_knee_j_arm_v1_latest.report.json"
)
SCHEMA = "compression_conditional_fusion_ablation_v2_codec_rerun_v1"

FROZEN_SAVING = 0.47538677918424754
FROZEN_J = 0.8904921794966301


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _frozen_gate() -> dict[str, Any]:
    live = _frozen_active()
    if not live.get("present"):
        return {"present": False}
    return {
        "present": True,
        "global_token_saving_rate": FROZEN_SAVING,
        "avg_reconstruction_fidelity_jaccard": FROZEN_J,
        "beat_baseline": "canonical_frozen_constants",
    }


def _baseline_j() -> float:
    if not BASELINE_V2.is_file():
        return 0.0
    bdoc = _load(BASELINE_V2) or {}
    return float(
        bdoc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )


def _active_caps() -> dict[str, Any]:
    return {
        "general_cap": 0.35,
        "sensitive_cap": 0.30,
        "hangul_cap": 0.60,
        "use_domain_relaxed": True,
        "use_master_codebook_lexicon_v1": True,
        "active_track_parity": True,
        "label": "active_caps_match_disk",
    }


def _knee_j_caps(knee: dict[str, Any]) -> dict[str, Any]:
    caps = (knee.get("knee_j_first") or {}).get("caps") or {}
    return {
        "general_cap": float(caps.get("general_max_saving_rate", 0.3)),
        "sensitive_cap": float(caps.get("sensitive_max_saving_rate", 0.26)),
        "hangul_cap": float(caps.get("hangul_max_saving_rate", 0.5)),
        "use_domain_relaxed": bool(caps.get("with_domain_relaxed", False)),
        "use_master_codebook_lexicon_v1": bool(caps.get("use_master_codebook_lexicon_v1", True)),
        "active_track_parity": bool(caps.get("active_track_parity", True)),
        "label": "knee_j_first_from_summary",
    }


def _run_codec_arm(doc: dict[str, Any], *, caps: dict[str, Any], bench_input: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    agg, report = evaluate_ng40_lane(
        doc,
        bench_input=bench_input,
        strategy="A",
        intensity="extreme",
        general_cap=caps["general_cap"],
        sensitive_cap=caps["sensitive_cap"],
        hangul_cap=caps["hangul_cap"],
        baseline_j=_baseline_j(),
        use_domain_relaxed=caps["use_domain_relaxed"],
        use_master_codebook_lexicon_v1=caps["use_master_codebook_lexicon_v1"],
        active_track_parity=caps["active_track_parity"],
    )
    return agg, report


def _case_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    return {str(c["id"]): c for c in cases if isinstance(c, dict) and c.get("id")}


def _aggregate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"case_count": 0}
    total_raw = sum(int(c.get("raw_tokens") or 0) for c in cases)
    total_comp = sum(int(c.get("compressed_tokens") or 0) for c in cases)
    jaccards = [float(c["reconstruction_fidelity_jaccard"]) for c in cases]
    global_saving = (1.0 - total_comp / total_raw) if total_raw else 0.0
    return {
        "case_count": len(cases),
        "global_token_saving_rate": round(global_saving, 6),
        "avg_reconstruction_fidelity_jaccard": round(sum(jaccards) / len(jaccards), 6),
        "min_reconstruction_fidelity_jaccard": round(min(jaccards), 6),
    }


def _delta_vs(base: dict[str, Any], arm: dict[str, Any]) -> dict[str, float]:
    return {
        "mean_saving_delta_pp": round(
            (float(arm["global_token_saving_rate"]) - float(base["global_token_saving_rate"])) * 100,
            4,
        ),
        "mean_jaccard_delta_pp": round(
            (float(arm["avg_reconstruction_fidelity_jaccard"]) - float(base["avg_reconstruction_fidelity_jaccard"]))
            * 100,
            4,
        ),
        "min_jaccard_delta_pp": round(
            (float(arm["min_reconstruction_fidelity_jaccard"]) - float(base["min_reconstruction_fidelity_jaccard"]))
            * 100,
            4,
        ),
    }


def _merge_conditional(
    *,
    routing_rows: list[dict[str, Any]],
    active_idx: dict[str, dict[str, Any]],
    knee_idx: dict[str, dict[str, Any]],
    policy_fn: Callable[[dict[str, Any]], str] = pick_policy,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    merged: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in routing_rows:
        cid = row["id"]
        policy = policy_fn(row)
        counts[policy] = counts.get(policy, 0) + 1
        source = knee_idx if policy == "knee_j_guard" else active_idx
        case = source.get(cid)
        if not case:
            raise KeyError(f"missing case {cid} in codec arm index")
        merged.append(
            {
                "id": cid,
                "policy": policy,
                "source_arm": "knee_j_codec" if policy == "knee_j_guard" else "active_codec",
                "shard_id": row.get("shard_id"),
                "reconstruction_error": row.get("reconstruction_error"),
                "token_saving_rate": case.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": case.get("reconstruction_fidelity_jaccard"),
                "raw_tokens": case.get("raw_tokens"),
                "compressed_tokens": case.get("compressed_tokens"),
            }
        )
    return merged, counts


def build(
    *,
    holdout_frac: float,
    skip_codec_rerun: bool,
    bench_input: Path,
    policy_fn: Callable[[dict[str, Any]], str] = pick_policy,
    schema: str = SCHEMA,
    theory_lane: str = "compression_conditional_fusion_codec_rerun",
    protocol_model: str = "merge(active_codec, knee_j_codec) per pick_policy",
    v2_compare_pointer: Path | None = None,
) -> dict[str, Any]:
    manifest = _load(ROUTING_MANIFEST)
    if not manifest:
        raise FileNotFoundError(f"missing routing manifest: {ROUTING_MANIFEST}")
    knee = _load(KNEE_SUMMARY) or {}
    proxy = _load(PROXY_V1)

    active_caps = _active_caps()
    knee_caps = _knee_j_caps(knee)

    if skip_codec_rerun:
        active_report = _load(ACTIVE_REPORT_OUT)
        knee_report = _load(KNEE_J_REPORT_OUT)
        if not active_report or not knee_report:
            raise FileNotFoundError(
                "skip_codec_rerun requires cached reports at "
                f"{ACTIVE_REPORT_OUT} and {KNEE_J_REPORT_OUT}"
            )
    else:
        if not bench_input.is_file():
            raise FileNotFoundError(f"missing bench input: {bench_input}")
        doc = json.loads(bench_input.read_text(encoding="utf-8-sig"))
        _, active_report = _run_codec_arm(doc, caps=active_caps, bench_input=bench_input)
        _, knee_report = _run_codec_arm(doc, caps=knee_caps, bench_input=bench_input)
        ACTIVE_REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_REPORT_OUT.write_text(json.dumps(active_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        KNEE_J_REPORT_OUT.write_text(json.dumps(knee_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    active_idx = _case_index(active_report)
    knee_idx = _case_index(knee_report)
    routing_rows = case_rows_from_manifest(manifest)
    if len(routing_rows) != 40:
        raise ValueError(f"expected 40 routing rows, got {len(routing_rows)}")

    merged_cases, policy_counts = _merge_conditional(
        routing_rows=routing_rows,
        active_idx=active_idx,
        knee_idx=knee_idx,
        policy_fn=policy_fn,
    )
    active_agg = _aggregate_cases(list(active_idx.values()))
    knee_agg = _aggregate_cases(list(knee_idx.values()))
    conditional_agg = _aggregate_cases(merged_cases)

    train_ids, holdout_ids = _holdout_split([r["id"] for r in routing_rows], holdout_frac)
    holdout_merged = [c for c in merged_cases if c["id"] in holdout_ids]
    holdout_active = [active_idx[cid] for cid in holdout_ids if cid in active_idx]
    holdout_cond = _aggregate_cases(holdout_merged)
    holdout_base = _aggregate_cases(holdout_active)

    frozen = _frozen_gate()
    beat_cond = _beat(conditional_agg, frozen) if frozen.get("present") else {"beat_frozen": False}
    compare_full = {
        "knee_j_global_codec": _delta_vs(active_agg, knee_agg),
        "conditional_vs_active_codec": _delta_vs(active_agg, conditional_agg),
    }
    compare_holdout = {
        "conditional_vs_active_codec": _delta_vs(holdout_base, holdout_cond),
    }
    ch = compare_holdout["conditional_vs_active_codec"]
    uplift_holdout = (
        ch["min_jaccard_delta_pp"] > 0
        and ch["mean_jaccard_delta_pp"] >= -0.5
        and ch["mean_saving_delta_pp"] >= -1.5
    )

    proxy_compare: dict[str, Any] | None = None
    if proxy:
        pv1 = (proxy.get("golden40_compare_holdout") or {}).get("conditional_fusion_v1") or {}
        proxy_compare = {
            "proxy_v1_min_j_delta_pp": round(float(pv1.get("min_jaccard_delta") or 0) * 100, 4),
            "v2_real_min_j_delta_pp": ch["min_jaccard_delta_pp"],
            "proxy_vs_real_min_j_gap_pp": round(
                ch["min_jaccard_delta_pp"] - float(pv1.get("min_jaccard_delta") or 0) * 100,
                4,
            ),
        }

    v2_compare: dict[str, Any] | None = None
    if v2_compare_pointer and v2_compare_pointer.is_file():
        v2doc = _load(v2_compare_pointer) or {}
        v2m = (v2doc.get("golden40_codec_arms") or {}).get("conditional_merged") or {}
        v2_compare = {
            "v2_conditional_saving": v2m.get("global_token_saving_rate"),
            "v2_conditional_min_j": v2m.get("min_reconstruction_fidelity_jaccard"),
            "v3_minus_v2_saving_pp": round(
                (float(conditional_agg["global_token_saving_rate"]) - float(v2m.get("global_token_saving_rate") or 0))
                * 100,
                4,
            ),
            "v3_minus_v2_min_j_pp": round(
                (
                    float(conditional_agg["min_reconstruction_fidelity_jaccard"])
                    - float(v2m.get("min_reconstruction_fidelity_jaccard") or 0)
                )
                * 100,
                4,
            ),
        }

    return {
        "schema": schema,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_forbidden": True,
        "theory_lane": theory_lane,
        "protocol": {
            "model": protocol_model,
            "codec_rerun": not skip_codec_rerun,
            "proxy_only": False,
            "holdout_frac": holdout_frac,
            "holdout_case_ids": sorted(holdout_ids),
            "note_ko": "real evaluate_report — not ACTIVE rewrite",
        },
        "cap_profiles": {
            "active_arm": active_caps,
            "knee_j_arm": knee_caps,
        },
        "codec_report_pointers": {
            "active_arm": str(ACTIVE_REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
            "knee_j_arm": str(KNEE_J_REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "frozen_baseline": frozen,
        "golden40_codec_arms": {
            "active_global": active_agg,
            "knee_j_global": knee_agg,
            "conditional_merged": conditional_agg,
        },
        "policy_counts": policy_counts,
        "beat_check_conditional_vs_frozen": beat_cond,
        "golden40_compare_full": compare_full,
        "golden40_holdout": {
            "active_codec": holdout_base,
            "conditional_merged": holdout_cond,
            "compare": compare_holdout,
        },
        "uplift_signal_holdout": uplift_holdout,
        "proxy_v1_compare": proxy_compare,
        "v2_compare": v2_compare,
        "verdict_ko": [
            f"conditional merged saving {conditional_agg['global_token_saving_rate']:.4f} "
            f"J {conditional_agg['avg_reconstruction_fidelity_jaccard']:.4f} "
            f"minJ {conditional_agg['min_reconstruction_fidelity_jaccard']:.4f}",
            f"beat_frozen={beat_cond.get('beat_frozen')} (promotion still forbidden without commander)",
            f"holdout min_j delta {ch['min_jaccard_delta_pp']} pp",
            "merge policy from routing manifest — ssot knee_j_guard cases use knee_j codec arm",
        ],
        "forbidden": [
            "merge conditional with ACTIVE 47% headline without beat_frozen",
            "apply_active from this ablation",
        ],
        "reproducible_command": (
            "py scripts/run_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py "
            f"--holdout-frac {holdout_frac}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--holdout-frac", type=float, default=0.2)
    ap.add_argument(
        "--skip-codec-rerun",
        action="store_true",
        help="Load cached codec reports from experiments/ (pytest / fast replay)",
    )
    args = ap.parse_args()

    doc = build(
        holdout_frac=args.holdout_frac,
        skip_codec_rerun=args.skip_codec_rerun,
        bench_input=args.bench_input if args.bench_input.is_absolute() else ROOT / args.bench_input,
    )
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "beat_frozen": doc["beat_check_conditional_vs_frozen"].get("beat_frozen"),
                "uplift_signal_holdout": doc["uplift_signal_holdout"],
                "conditional_min_j": doc["golden40_codec_arms"]["conditional_merged"]["min_reconstruction_fidelity_jaccard"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
