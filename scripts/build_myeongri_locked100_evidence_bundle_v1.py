#!/usr/bin/env python3
"""Consolidate locked_eval 100 harness + Pack0B dual-report SSOT (research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/myeongri_locked100_evidence_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    harness_s32_hn = _load(
        ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_interpret_s32_hn_v1.json"
    )
    harness_interp = _load(
        ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_interpret_lora_s16_v1.json"
    )
    harness_focus = _load(
        ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_focus0007_v1.json"
    )
    pillars_ganji = _load(
        ROOT / "reports/myeongri_locked_eval_inference_eval_pillars_ganji_train1000_s64_locked100_pillars_v1.json"
    )
    pillars_chain = _load(ROOT / "reports/myeongri_pillars_ganji_exact_chain_v1_latest.json")
    pack0b_raw = _load(
        ROOT / "reports/myeongri_locked_eval_inference_eval_qwen_safe_managed_locked100_raw.json"
    )
    pack0b_repair = _load(
        ROOT / "reports/myeongri_locked_eval_inference_eval_qwen_safe_managed_locked100_repair_v2.json"
    )
    compare = _load(ROOT / "reports/myeongri_harness_interpret_adapter_compare_locked100_v1_latest.json")

    raw_align = float(pack0b_raw.get("alignment_pass_rate") or 0)
    repair_align = float(pack0b_repair.get("alignment_pass_rate") or 0)

    doc = {
        "schema": "myeongri_locked100_evidence_bundle_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "track_a_blocked": True,
        "track_a_gate": "alignment_pass_rate(raw)",
        "eval_slice": "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl (100 rows)",
        "architecture": "harness_v2_engine_plus_interpret",
        "harness_v2": {
            "interpret_lora_s32_hn": {
                "report": "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_interpret_s32_hn_v1.json",
                "adapter": "storage/adapters/myeongri_interpret_lora_v0/run_interpret_harness_train_s32_hn_v1",
                "engine_pillars_pass_rate": harness_s32_hn.get("engine_pillars_pass_rate"),
                "interpret_envelope_parse_ok_rate": harness_s32_hn.get("interpret_envelope_parse_ok_rate"),
                "interpret_envelope_coerced_rate": harness_s32_hn.get("interpret_envelope_coerced_rate"),
            },
            "interpret_lora_s16": {
                "report": "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_interpret_lora_s16_v1.json",
                "adapter": "storage/adapters/myeongri_interpret_lora_v0/run_interpret_harness_train_s16_v1",
                "engine_pillars_pass_rate": harness_interp.get("engine_pillars_pass_rate"),
                "interpret_envelope_parse_ok_rate": harness_interp.get("interpret_envelope_parse_ok_rate"),
                "interpret_envelope_coerced_rate": harness_interp.get("interpret_envelope_coerced_rate"),
            },
            "pack0b_focus0007_baseline": {
                "report": "reports/myeongri_harness_v2_engine_interpret_smoke_locked100_focus0007_v1.json",
                "adapter": "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_compact_focus0007_s8_v1",
                "engine_pillars_pass_rate": harness_focus.get("engine_pillars_pass_rate"),
                "interpret_envelope_parse_ok_rate": harness_focus.get("interpret_envelope_parse_ok_rate"),
                "interpret_envelope_coerced_rate": harness_focus.get("interpret_envelope_coerced_rate"),
            },
            "compare": "reports/myeongri_harness_interpret_adapter_compare_locked100_v1_latest.json",
        },
        "pack0b_pillars_ganji_exact_lane": {
            "status": "research_deprioritized",
            "chain": "reports/myeongri_pillars_ganji_exact_chain_v1_latest.json",
            "eval_report": "reports/myeongri_locked_eval_inference_eval_pillars_ganji_train1000_s64_locked100_pillars_v1.json",
            "adapter": "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_pillars_ganji_train1000_s64_v1",
            "parse_ok_rate": pillars_ganji.get("parse_ok_rate"),
            "pillars_alignment_pass_rate": pillars_ganji.get("pillars_alignment_pass_rate"),
            "note": pillars_chain.get("conclusion", {}).get("note")
            if isinstance(pillars_chain.get("conclusion"), dict)
            else "LoRA pillars curriculum: parse ok, ganji align 0 — engine remains SSOT",
        },
        "pack0b_full_json_eval": {
            "raw": {
                "report": "reports/myeongri_locked_eval_inference_eval_qwen_safe_managed_locked100_raw.json",
                "predictions": "reports/myeongri_locked_eval_predictions_qwen_safe_managed_locked100_raw.jsonl",
                "parse_ok_rate": pack0b_raw.get("parse_ok_rate"),
                "alignment_pass_rate": raw_align,
                "label": "model_core_gate",
            },
            "repair_v2": {
                "report": "reports/myeongri_locked_eval_inference_eval_qwen_safe_managed_locked100_repair_v2.json",
                "predictions": "reports/myeongri_locked_eval_predictions_qwen_safe_managed_locked100_repair_v2.jsonl",
                "parse_ok_rate": pack0b_repair.get("parse_ok_rate"),
                "alignment_pass_rate": repair_align,
                "repair_applied_count": pack0b_repair.get("deterministic_repair_v2_applied_count"),
                "label": "operational_post_processor_only",
            },
            "delta": {
                "alignment_pass_rate_delta_repair_v2_minus_raw": round(repair_align - raw_align, 6),
            },
        },
        "messaging": {
            "allowed": "raw remains below gate; repair_v2 improves operational consistency.",
            "disallowed": "model reached gate from repair_v2 uplift alone",
        },
        "router": compare.get("conclusion") or {"route_mode": "harness_v2_engine_plus_interpret"},
        "operational_routing_frozen": {
            "engine": "prep_myeongri_deterministic_lora_golden_v1.build_golden_row_dict",
            "interpret_primary": "storage/adapters/myeongri_interpret_lora_v0/run_interpret_harness_train_s32_hn_v1",
            "interpret_zero_coercion_fallback": "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_compact_focus0007_s8_v1",
            "pack0b_full_json_ops": "focus0007 + repair_v2 (operational only)",
            "pillars_via_lora": False,
        },
    }

    out = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "track_a_blocked": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
