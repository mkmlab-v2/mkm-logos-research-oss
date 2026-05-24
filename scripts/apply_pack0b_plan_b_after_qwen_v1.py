#!/usr/bin/env python3
"""Resolve Pack 0-B Plan B branch from post-train eval + Harness v2 pointers.

Reads pillars_alignment_pass_rate from eval report, picks branch (>5% vs <=5%),
and merges architecture pivot (Harness v2) when pillars fail. Does not start training.

Example::

  py scripts/apply_pack0b_plan_b_after_qwen_v1.py \\
    --eval-json reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json"
DEFAULT_PLAN = ROOT / "reports/pack0b_plan_b_after_qwen_v1_latest.json"
DEFAULT_HARNESS = ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/pack0b_plan_b_resolution_merged_v1_latest.json"
THRESHOLD = 0.05


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--harness-json", type=Path, default=DEFAULT_HARNESS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    args = ap.parse_args()

    if not args.eval_json.is_file():
        print(f"missing eval report: {args.eval_json}", file=sys.stderr)
        return 2

    ev = json.loads(args.eval_json.read_text(encoding="utf-8"))
    rate = float(ev.get("pillars_alignment_pass_rate", ev.get("alignment_pass_rate", 0.0)))
    parse_rate = float(ev.get("parse_ok_rate", 0.0))
    rows = int(ev.get("rows", 0))

    harness_doc: dict | None = None
    engine_rate: float | None = None
    if args.harness_json.is_file():
        harness_doc = json.loads(args.harness_json.read_text(encoding="utf-8"))
        engine_rate = float(harness_doc.get("engine_pillars_pass_rate", 0.0))

    if rate > args.threshold:
        branch_id = "expand_qwen_compact"
        branch_ko = "pillars > 5% — full locked_eval·스텝 확대 검토"
        next_commands = [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-Pack0bQwenPostTrainEval_v1.ps1 -FullLockedEval",
            "py scripts/run_pack0b_deterministic_lora_pipeline_v1.py --run-train --train-steps 500 --train-resume-from-last-checkpoint ...",
        ]
    else:
        branch_id = "plan_b_sft_v2_or_harness_v2"
        branch_ko = (
            "pillars <= 5% — Plan B SFT v2 재변환·재학습(선택) + "
            "권장: Harness v2(엔진 계산 + LLM 해설만)"
        )
        next_commands = [
            "py scripts/convert_myeongri_golden_to_sft_instruction_jsonl_v1.py "
            "--input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl "
            "--output-jsonl data/training/myeongri_deterministic_lora_sft_compact_qwen_train_v2.jsonl "
            "--compact-output",
            "py scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py --limit 5",
            "# optional GPU (external terminal):",
            "py scripts/run_pack0b_deterministic_lora_pipeline_v1.py "
            "--sft-jsonl data/training/myeongri_deterministic_lora_sft_compact_qwen_train_v2.jsonl "
            "--adapter-out storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_compact_v2 "
            "--compact-sft --profile train_default --run-train --train-steps 500",
        ]

    primary_architecture = (
        "harness_v2_engine_plus_interpret"
        if rate <= args.threshold and engine_rate is not None and engine_rate >= 1.0
        else "pack0b_lora_pillars"
        if rate > args.threshold
        else "plan_b_sft_v2_retry"
    )

    merged = {
        "schema": "pack0b_plan_b_resolution_merged_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "eval_report": str(args.eval_json.relative_to(ROOT)).replace("\\", "/"),
        "metrics": {
            "pillars_alignment_pass_rate": rate,
            "parse_ok_rate": parse_rate,
            "eval_rows": rows,
            "threshold": args.threshold,
        },
        "resolved_branch_id": branch_id,
        "resolved_branch_ko": branch_ko,
        "primary_architecture_recommendation": primary_architecture,
        "harness_v2": {
            "report": str(args.harness_json.relative_to(ROOT)).replace("\\", "/")
            if harness_doc
            else None,
            "engine_pillars_pass_rate": engine_rate,
            "interpret_envelope_parse_ok_rate": harness_doc.get("interpret_envelope_parse_ok_rate")
            if harness_doc
            else None,
            "smoke_script": "scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py",
        },
        "next_commands": next_commands,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.plan_json.is_file():
        plan = json.loads(args.plan_json.read_text(encoding="utf-8"))
        plan["last_resolution"] = {
            "generated_at_utc": merged["generated_at_utc"],
            "pillars_alignment_pass_rate": rate,
            "resolved_branch_id": branch_id,
            "primary_architecture_recommendation": primary_architecture,
            "merged_report": str(args.out_json.relative_to(ROOT)).replace("\\", "/"),
        }
        args.plan_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "pillars_alignment_pass_rate": rate,
                "resolved_branch_id": branch_id,
                "primary_architecture": primary_architecture,
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
