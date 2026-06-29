#!/usr/bin/env python3
"""One-screen B-track sign-off brief: MKM12 A-code 12-pack vs bench 4×40 wall."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT = ROOT / "reports/lora_tranche2_acode_mkm12_signoff_brief_latest.json"

POINTERS = {
    "acode_registry": ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json",
    "router_smoke": ROOT / "reports/lora_tranche2_mkm12_75_to_12_router_smoke_latest.json",
    "acode_train_ablation": ROOT / "reports/lora_tranche2_qwen12pack_acode_train_ablation_latest.json",
    "acode_expanded_eval": ROOT / "reports/lora_tranche2_qwen12pack_acode_locked_eval_expanded_latest.json",
    "closure_bundle": ROOT / "reports/lora_tranche2_closure_bundle_v1_latest.json",
    "signoff_pack": ROOT / "reports/lora_tranche2_signoff_pack_v1_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_brief() -> dict[str, Any]:
    registry = _read(POINTERS["acode_registry"])
    router = _read(POINTERS["router_smoke"])
    train = _read(POINTERS["acode_train_ablation"])
    expanded = _read(POINTERS["acode_expanded_eval"])
    closure = _read(POINTERS["closure_bundle"])
    signoff = _read(POINTERS["signoff_pack"])

    tw = registry.get("track_wall", {})
    fls = registry.get("fact_lock_status", {})

    return {
        "schema": "lora_tranche2_acode_mkm12_signoff_brief_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "purpose_ko": "지휘관 B-track review용 한 화면 — 상용 GO 아님",
        "lanes": {
            "eval_routing_ssot": signoff.get("recommendation", {}).get("eval_routing_ssot", "bench_4x40"),
            "mkm12_expansion_lane": "hier_12x75_hybrid",
            "bench_4x40_forced_alias_forbidden": tw.get("bench_4x40_forced_pack_alias_forbidden"),
            "promotion_to_a_track_allowed": tw.get("promotion_to_a_track_allowed"),
        },
        "acode_engineering_proof": {
            "router_75_slots": router.get("slot_count"),
            "router_wired_ok": router.get("routing_wired_ok"),
            "shard_mode": train.get("shard_mode"),
            "distinct_adapters": train.get("diversity", {}).get("distinct_weight_hashes"),
            "diversity_ok": train.get("diversity", {}).get("diversity_ok"),
            "attach_total_sec": train.get("trained_adapter_attach", {}).get("total_attach_sec"),
        },
        "quality_smoke": {
            "micro_ablation_alignment": "see per-pack locked_eval in train ablation (limit 2)",
            "expanded_eval_mean_alignment": expanded.get("summary", {}).get("mean_alignment_pass_rate"),
            "expanded_eval_present": POINTERS["acode_expanded_eval"].is_file(),
        },
        "go_flags": {
            "multi_pack_production_go": train.get("multi_pack_production_go"),
            "acode12pack_multi_pack_production_go": train.get("multi_pack_production_go"),
            "closure_ok_bench_btrack": closure.get("closure_ok"),
            "allow_deploy_multipack_btrack": signoff.get("gates", {}).get("allow_deploy_multipack_btrack"),
        },
        "not_authorized_ko": [
            "Track A / MS 압축 본선 자동 승격",
            "실매매 LoRA deploy",
            "bench 4×40 라벨을 A-code 12팩에 강제 매핑",
        ],
        "next_human_gate_ko": fls.get("next_human_gate"),
        "artifact_pointers": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in POINTERS.items()},
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build A-code MKM12 sign-off brief JSON.")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    p.add_argument("--stdout-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    brief = build_brief()
    text = json.dumps(brief, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(text)
        return 0
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
