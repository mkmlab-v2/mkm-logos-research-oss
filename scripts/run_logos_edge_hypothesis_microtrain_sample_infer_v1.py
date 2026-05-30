#!/usr/bin/env python3
"""Sample inference for Logos edge-hypothesis micro-train adapter ([HYPO] B-track).

Runs 1–2 held prompts from the SFT JSONL through TinyLlama + LoRA adapter and
checks advisory format guards (non-blocking smoke; not promotion GO).
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_v1_latest.jsonl"
DEFAULT_ADAPTER = ROOT / "reports/logos_edge_hypothesis_microtrain_v1"
DEFAULT_MICRO_REPORT = ROOT / "reports/logos_edge_hypothesis_microtrain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_edge_hypothesis_microtrain_sample_infer_v1_latest.json"
DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
        if limit > 0 and len(rows) >= limit:
            break
    return rows


def _build_prompt(instruction: str) -> str:
    return f"### Instruction:\n{instruction}\n### Response:\n"


def _score_output(text: str) -> dict[str, Any]:
    lower = text.lower()
    checks = {
        "has_hypo_tag": "[HYPO]" in text,
        "mentions_research_only": "research_only" in lower or "research only" in lower,
        "mentions_non_gating": "non_gating" in lower or "non-gating" in lower or "non gating" in lower,
        "mentions_merge_wall": "merge_to_canonical_allowed=false" in lower
        or "merge_to_canonical_allowed = false" in lower
        or "canonical" in lower and "false" in lower,
    }
    checks["format_smoke_ok"] = checks["has_hypo_tag"] and (
        checks["mentions_research_only"] or checks["mentions_non_gating"]
    )
    return checks


def _load_model(model_name: str, adapter_path: Path | None):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    if adapter_path is not None:
        model = PeftModel.from_pretrained(model, str(adapter_path))
    model.eval()
    return model, tokenizer


def _generate(model, tokenizer, instruction: str, max_new_tokens: int) -> tuple[str, float]:
    import torch

    prompt = _build_prompt(instruction)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    t0 = time.perf_counter()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    full = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    if "### Response:" in full:
        return full.split("### Response:", 1)[1].strip(), elapsed_ms
    # strip echoed instruction tail if present
    if instruction[:40] in full:
        tail = full.split(instruction[: min(80, len(instruction))], 1)[-1]
        return tail.strip(), elapsed_ms
    return full.strip(), elapsed_ms


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--adapter-path", type=Path, default=DEFAULT_ADAPTER)
    ap.add_argument("--micro-report", type=Path, default=DEFAULT_MICRO_REPORT)
    ap.add_argument("--model-name", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="Load prompts only; no model")
    args = ap.parse_args()

    if args.micro_report.is_file():
        micro = json.loads(args.micro_report.read_text(encoding="utf-8-sig"))
        if micro.get("model_name"):
            args.model_name = str(micro["model_name"])
        if micro.get("adapter_out") and args.adapter_path == DEFAULT_ADAPTER:
            args.adapter_path = ROOT / str(micro["adapter_out"])

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 1
    if not args.dry_run and not (args.adapter_path / "adapter_config.json").is_file():
        print(json.dumps({"ok": False, "error": f"missing adapter: {args.adapter_path}"}))
        return 1

    rows = _load_jsonl(args.jsonl, args.limit)
    if not rows:
        print(json.dumps({"ok": False, "error": "no rows"}))
        return 1

    samples: list[dict[str, Any]] = []
    if args.dry_run:
        for i, row in enumerate(rows, start=1):
            samples.append(
                {
                    "sample_index": i,
                    "instruction_preview": row["instruction"][:120] + "...",
                    "expected_output_preview": row["output"][:120] + "...",
                    "dry_run": True,
                }
            )
        report = {
            "schema": "logos_edge_hypothesis_microtrain_sample_infer_v1",
            "generated_at_utc": _utc_now(),
            "dry_run": True,
            "sample_count": len(samples),
            "samples": samples,
            "overall_format_smoke_ok": True,
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "samples": len(samples)}))
        return 0

    model, tokenizer = _load_model(args.model_name, args.adapter_path)
    format_ok = 0
    for i, row in enumerate(rows, start=1):
        pred, latency_ms = _generate(model, tokenizer, row["instruction"], args.max_new_tokens)
        scores = _score_output(pred)
        if scores["format_smoke_ok"]:
            format_ok += 1
        samples.append(
            {
                "sample_index": i,
                "instruction_preview": row["instruction"][:160],
                "expected_output_preview": row["output"][:160],
                "prediction": pred[:800],
                "prediction_chars": len(pred),
                "latency_ms": round(latency_ms, 2),
                "scores": scores,
                "metadata": row.get("metadata"),
            }
        )

    overall = format_ok == len(samples) and len(samples) > 0
    report = {
        "schema": "logos_edge_hypothesis_microtrain_sample_infer_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "model_name": args.model_name,
        "adapter_path": str(args.adapter_path).replace("\\", "/"),
        "sample_count": len(samples),
        "format_smoke_pass_count": format_ok,
        "overall_format_smoke_ok": overall,
        "samples": samples,
        "note": "Format smoke only; not semantic edge quality or promotion GO.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall, "format_smoke_pass_count": format_ok, "sample_count": len(samples)}))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
