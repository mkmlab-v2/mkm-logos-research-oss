#!/usr/bin/env python3
"""Assemble LoRA tranche-2 B-track signoff evidence pack (routing + ops + GPU).

research_only — B-track evidence; multi-pack deploy follows lora_tranche2_multipack_* signoff (Track A OFF).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT = ROOT / "docs/final/artifacts/lora_tranche2_signoff_pack_v1_latest.json"
DEFAULT_REPORTS_OUT = ROOT / "reports/lora_tranche2_signoff_pack_v1_latest.json"

INPUTS = {
    "architecture_sweep": ROOT / "reports/lora_domain_architecture_sweep_latest.json",
    "latency_extrapolation": ROOT / "reports/lora_pack_latency_extrapolation_latest.json",
    "gpu_ablation": ROOT / "reports/lora_domain_architecture_gpu_ablation_latest.json",
    "stub_swap_ablation": ROOT / "reports/lora_distinct_adapter_stub_swap_ablation_latest.json",
    "go_no_go": ROOT / "reports/lora_pack_go_no_go_latest.json",
    "human_signoff": ROOT / "reports/lora_pack_human_signoff_latest.json",
    "release_candidate": ROOT / "reports/release_candidate_latest.json",
    "efficiency_search": ROOT / "reports/lora_pack_qwen_efficiency_search_latest.json",
    "microtrain_diversity": ROOT / "reports/lora_tranche2_microtrain_diversity_probe_latest.json",
    "qwen4pack_train_ablation": ROOT / "reports/lora_tranche2_qwen4pack_train_ablation_latest.json",
    "multipack_human_signoff": ROOT / "reports/lora_tranche2_multipack_human_signoff_latest.json",
    "multipack_go_no_go": ROOT / "reports/lora_tranche2_multipack_go_no_go_latest.json",
    "hybrid12_microtrain": ROOT / "reports/lora_tranche2_hybrid12pack_microtrain_diversity_probe_latest.json",
    "qwen4pack_locked_eval_expanded": ROOT / "reports/lora_tranche2_qwen4pack_locked_eval_expanded_latest.json",
    "trackc_copy": ROOT / "docs/final/artifacts/lora_tranche2_trackc_copy_v1_latest.json",
    "acode_12_pack_registry": ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json",
    "mkm12_acode_router_smoke": ROOT / "reports/lora_tranche2_mkm12_75_to_12_router_smoke_latest.json",
    "qwen12pack_acode_train_ablation": ROOT / "reports/lora_tranche2_qwen12pack_acode_train_ablation_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_pack() -> dict[str, Any]:
    loaded = {k: _read_json(p) for k, p in INPUTS.items()}
    sweep = loaded["architecture_sweep"]
    gpu = loaded["gpu_ablation"]
    go = loaded["go_no_go"]
    stub = loaded["stub_swap_ablation"]
    micro = loaded["microtrain_diversity"]
    qwen4 = loaded["qwen4pack_train_ablation"]
    mp_signoff = loaded["multipack_human_signoff"]
    mp_go = loaded["multipack_go_no_go"]
    hybrid12 = loaded["hybrid12_microtrain"]
    expanded_eval = loaded["qwen4pack_locked_eval_expanded"]
    trackc = loaded["trackc_copy"]
    acode_registry = loaded["acode_12_pack_registry"]
    acode_router = loaded["mkm12_acode_router_smoke"]
    qwen12_acode = loaded["qwen12pack_acode_train_ablation"]

    acode_expanded_path = ROOT / "reports/lora_tranche2_qwen12pack_acode_locked_eval_expanded_latest.json"
    acode_expanded = _read_json(acode_expanded_path) if acode_expanded_path.is_file() else {}

    verdict = sweep.get("verdict", {})
    hybrid_uplift = sweep.get("hybrid_routing_uplift", {})

    qwen4_diversity_ok = qwen4.get("diversity", {}).get("diversity_ok") is True
    multipack_approved = mp_signoff.get("approved") is True and mp_go.get("allow_deploy_multipack_btrack") is True
    if multipack_approved:
        multi_pack_status = "GO (bench 4×40 B-track · commander sign-off)"
    elif qwen4_diversity_ok:
        multi_pack_status = "HOLD until human sign-off (Qwen 4-pack ablation complete)"
    else:
        multi_pack_status = "HOLD until distinct-adapter training ablation + human sign-off"

    recommendation = {
        "eval_routing_ssot": "bench_4x40",
        "mkm12_expansion_lane": "hier_12x75_hybrid",
        "vision_20x200": "WATCH",
        "rc_factory_single_pack": "GO",
        "multi_pack_weight_expansion": multi_pack_status,
    }

    gates = {
        "rc_validation_passed": bool(go.get("validation_passed")),
        "human_signoff_approved": bool(go.get("human_signoff_approved")),
        "allow_deploy_single_pack": bool(go.get("allow_deploy")),
        "research_only_multi_pack": True,
        "vision_20x200_optimal": bool(verdict.get("vision_is_optimal")),
        "sweep_best_id": verdict.get("best_candidate_id"),
        "hybrid_hit_rate": hybrid_uplift.get("K75_hybrid_hit_rate"),
        "gpu_ablation_status": gpu.get("status"),
        "stub_swap_status": stub.get("status"),
        "microtrain_diversity_ok": micro.get("diversity", {}).get("diversity_ok"),
        "microtrain_distinct_hashes": micro.get("diversity", {}).get("distinct_weight_hashes"),
        "qwen4pack_diversity_ok": qwen4.get("diversity", {}).get("diversity_ok"),
        "qwen4pack_distinct_hashes": qwen4.get("diversity", {}).get("distinct_weight_hashes"),
        "qwen4pack_attach_total_sec": qwen4.get("trained_adapter_attach", {}).get("total_attach_sec"),
        "multipack_human_signoff_approved": mp_signoff.get("approved"),
        "allow_deploy_multipack_btrack": mp_go.get("allow_deploy_multipack_btrack"),
        "hybrid12_diversity_ok": hybrid12.get("diversity", {}).get("diversity_ok"),
        "expanded_eval_mean_alignment": expanded_eval.get("summary", {}).get("mean_alignment_pass_rate"),
        "acode_registry_routing_implemented": acode_registry.get("fact_lock_status", {}).get(
            "routing_implemented"
        ),
        "acode_router_smoke_ok": acode_router.get("routing_wired_ok") is True,
        "acode_router_slot_count": acode_router.get("slot_count"),
        "acode12pack_shard_mode": qwen12_acode.get("shard_mode"),
        "acode12pack_diversity_ok": qwen12_acode.get("diversity", {}).get("diversity_ok"),
        "acode12pack_distinct_hashes": qwen12_acode.get("diversity", {}).get("distinct_weight_hashes"),
        "acode12pack_attach_total_sec": qwen12_acode.get("trained_adapter_attach", {}).get("total_attach_sec"),
        "acode12pack_multi_pack_production_go": qwen12_acode.get("multi_pack_production_go"),
        "acode12pack_expanded_mean_alignment": acode_expanded.get("summary", {}).get(
            "mean_alignment_pass_rate"
        ),
    }

    tranche2_ready = (
        gates["sweep_best_id"] == "bench_4x40"
        and not gates["vision_20x200_optimal"]
        and float(hybrid_uplift.get("K75_hybrid_hit_rate") or 0) >= 0.9
        and gpu.get("status") == "ok"
        and (micro.get("diversity", {}).get("diversity_ok") is True or not micro)
        and (qwen4.get("diversity", {}).get("diversity_ok") is True or not qwen4)
        and (hybrid12.get("diversity", {}).get("diversity_ok") is True or not hybrid12)
        and (multipack_approved or not mp_signoff)
        and (expanded_eval.get("summary") is not None or not expanded_eval)
    )

    pack: dict[str, Any] = {
        "schema": "lora_tranche2_signoff_pack_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "tranche2_btrack_ready": tranche2_ready,
        "recommendation": recommendation,
        "gates": gates,
        "summary_ko": (
            "Tranche 2 B-track: Golden-40 routing favors 4×40; MKM12 SSOT favors 12×75 hybrid (v61+shard); "
            "20×200 vision is not optimal. RC 1-pack factory GO; multi-pack "
            + ("GO (B-track commander sign-off)." if multipack_approved else "HOLD pending sign-off.")
        ),
        "artifact_inputs": {k: _rel(p) for k, p in INPUTS.items()},
        "artifact_exists": {k: p.is_file() for k, p in INPUTS.items()},
        "verdict_excerpt": verdict,
        "hybrid_routing_uplift": hybrid_uplift,
        "gpu_ablation_excerpt": {
            "measurement_session": gpu.get("measurement_session"),
            "scenarios": gpu.get("scenarios"),
            "verdict_ko": gpu.get("verdict_ko"),
        },
        "stub_swap_excerpt": {
            "scenarios": stub.get("scenarios"),
            "verdict_ko": stub.get("verdict_ko"),
        },
        "latency_excerpt": loaded["latency_extrapolation"].get("comparison_ko"),
        "rc_excerpt": {
            "release_tag": loaded["release_candidate"].get("release_tag") or go.get("release_tag"),
            "efficiency_200_200": loaded["efficiency_search"].get("packs_done"),
        },
        "microtrain_excerpt": {
            "diversity": micro.get("diversity"),
            "packs": micro.get("packs"),
            "verdict_ko": micro.get("verdict_ko"),
        },
        "qwen4pack_excerpt": {
            "diversity": qwen4.get("diversity"),
            "trained_adapter_attach": qwen4.get("trained_adapter_attach"),
            "verdict_ko": qwen4.get("verdict_ko"),
            "multi_pack_production_go": multipack_approved,
        },
        "multipack_signoff_excerpt": {
            "approved": mp_signoff.get("approved"),
            "decision": mp_signoff.get("decision"),
            "scope": mp_signoff.get("scope"),
            "note_ko": mp_signoff.get("note_ko"),
        },
        "expanded_eval_excerpt": expanded_eval.get("summary"),
        "hybrid12_excerpt": hybrid12.get("diversity"),
        "acode_mkm12_excerpt": {
            "registry_fact_lock": acode_registry.get("fact_lock_status"),
            "router_smoke": {
                "slot_count": acode_router.get("slot_count"),
                "distinct_packs": acode_router.get("distinct_packs"),
                "routing_wired_ok": acode_router.get("routing_wired_ok"),
            },
            "qwen12pack_acode": {
                "shard_mode": qwen12_acode.get("shard_mode"),
                "diversity": qwen12_acode.get("diversity"),
                "trained_adapter_attach": qwen12_acode.get("trained_adapter_attach"),
                "multi_pack_production_go": qwen12_acode.get("multi_pack_production_go"),
                "verdict_ko": qwen12_acode.get("verdict_ko"),
            },
            "acode_expanded_eval": acode_expanded.get("summary"),
            "signoff_brief": "reports/lora_tranche2_acode_mkm12_signoff_brief_latest.json",
            "track_wall_note_ko": (
                "MKM12 A-code 12팩(hier_12x75_hybrid)은 bench 4×40 eval 레인과 격벽. "
                "multi_pack_production_go=false 고정."
            ),
        },
        "trackc_copy_excerpt": {
            "one_liner_ko": trackc.get("one_liner_ko"),
            "bullets_ko": trackc.get("bullets_ko"),
            "disclaimer_ko": trackc.get("disclaimer_ko"),
        },
        "reproduction_commands": [
            "py scripts/build_lora_domain_architecture_sweep_v1.py",
            "py scripts/build_lora_pack_latency_extrapolation_v1.py",
            "py scripts/run_lora_domain_architecture_gpu_ablation_v1.py --max-swap-probes 2 --max-new-tokens 96",
            "py scripts/run_lora_distinct_adapter_stub_swap_ablation_v1.py --refresh-stubs --max-packs 20",
            "py scripts/run_lora_tranche2_microtrain_diversity_probe_v1.py --pack-count 3 --train-steps 12 --rows-per-pack-cap 80",
            "py scripts/run_lora_tranche2_qwen4pack_train_ablation_v1.py --pack-count 4 --train-steps 12 --rows-per-pack-cap 60",
            "py scripts/run_lora_tranche2_microtrain_diversity_probe_v1.py --pack-count 12 --train-steps 8 --rows-per-pack-cap 40 --out-json reports/lora_tranche2_hybrid12pack_microtrain_diversity_probe_latest.json --work-root reports/lora_tranche2_hybrid12pack_v1",
            "py scripts/apply_lora_tranche2_multipack_human_approval_v1.py",
            "py scripts/run_lora_tranche2_qwen4pack_locked_eval_expanded_v1.py --eval-limit 10 --skip-if-report",
            "py scripts/build_acode_12_pack_slot_overrides_v1.py --write",
            "py scripts/build_lora_tranche2_mkm12_75_to_12_router_smoke_v1.py",
            "py scripts/run_lora_tranche2_qwen12pack_train_ablation_v1.py --work-root reports/lora_tranche2_qwen12pack_acode_v1 --out-json reports/lora_tranche2_qwen12pack_acode_train_ablation_latest.json",
            "py scripts/run_lora_tranche2_qwen12pack_acode_locked_eval_expanded_v1.py --eval-limit 100 --skip-if-report",
            "py scripts/build_lora_tranche2_acode_mkm12_signoff_brief_v1.py",
            "py scripts/build_lora_tranche2_trackc_copy_v1.py",
            "py scripts/build_lora_tranche2_signoff_pack_v1.py",
            "py scripts/build_lora_tranche2_closure_bundle_v1.py",
        ],
        "policy_pointers": {
            "track_c_plan": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
            "public_facing": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "research_queue": "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md (RQ-023)",
        },
        "disclaimer": (
            "B-track bench 4×40 scope when multipack signoff approved. "
            "Not Track A·MS·live-trading authorization. "
            "12/20-pack production lanes remain separate human gates."
        ),
    }
    return pack


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build LoRA tranche-2 signoff pack.")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    p.add_argument("--reports-json", default=str(DEFAULT_REPORTS_OUT))
    p.add_argument("--stdout-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pack = build_pack()
    text = json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(text)
        return 0
    for out in (Path(args.out_json), Path(args.reports_json)):
        path = out if out.is_absolute() else ROOT / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"WROTE: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
