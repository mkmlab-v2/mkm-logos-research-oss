#!/usr/bin/env python3
"""Run batch inference for MKM control-integrity LoRA dataset.

Input JSONL rows should contain:
- id (preferred) OR sample_id
- instruction

Output JSONL rows:
{"id":"...", "prediction":"..."}
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = WORKSPACE_ROOT / "data" / "training" / "mkm_control_integrity_lora_splits_v1" / "test.jsonl"
DEFAULT_OUT = WORKSPACE_ROOT / "reports" / "mkm_control_integrity_predictions_test_latest.jsonl"
DEFAULT_SSOT_PROFILES = (
    WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "mkm_control_integrity_lora_model_profiles_v1.json"
)


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_no}: invalid json: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path} line {line_no}: row must be object")
            rows.append(row)
    return rows


def _row_id(row: dict[str, Any], idx: int) -> str:
    rid = str(row.get("id") or row.get("sample_id") or f"row-{idx:06d}")
    return rid


def _resolve_model_from_ssot(cli_model: str, ssot_path: Path | None, ssot_key: str | None) -> tuple[str, bool]:
    if not ssot_path or not ssot_key:
        return cli_model, False
    if not ssot_path.is_file():
        return cli_model, False
    try:
        doc = json.loads(ssot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cli_model, False
    profs = doc.get("profiles")
    if not isinstance(profs, dict):
        return cli_model, False
    prof = profs.get(ssot_key)
    if not isinstance(prof, dict):
        return cli_model, False
    mid = prof.get("model_id")
    if isinstance(mid, str) and mid.strip():
        return mid.strip(), True
    return cli_model, False


def _percentiles_ms(lat_ms: list[float]) -> dict[str, float]:
    if not lat_ms:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "count": 0}
    lat_ms_sorted = sorted(lat_ms)
    n = len(lat_ms_sorted)

    def pct(p: float) -> float:
        if n == 1:
            return float(lat_ms_sorted[0])
        k = (n - 1) * (p / 100.0)
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return float(lat_ms_sorted[lo] + (k - lo) * (lat_ms_sorted[hi] - lat_ms_sorted[lo]))

    return {
        "mean_ms": round(float(statistics.mean(lat_ms)), 3),
        "p50_ms": round(pct(50), 3),
        "p95_ms": round(pct(95), 3),
        "p99_ms": round(pct(99), 3),
        "count": n,
    }


def _build_prompt(instruction: str) -> str:
    return f"### Instruction:\n{instruction}\n### Response:\n"


def _load_model_and_tokenizer(model_name: str, adapter_path: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        device_map="auto",
    )
    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return model, tokenizer


def _generate_one(model, tokenizer, instruction: str, max_new_tokens: int, temperature: float, top_p: float) -> str:
    import torch

    prompt = _build_prompt(instruction)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    full = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    if "### Response:" in full:
        return full.split("### Response:", 1)[1].strip()
    return full.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch inference for MKM control-integrity LoRA split")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_IN), help="Input split JSONL path")
    ap.add_argument("--out", dest="output_path", default=str(DEFAULT_OUT), help="Output predictions JSONL path")
    ap.add_argument("--model-name", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0", help="Base model")
    ap.add_argument("--adapter-path", default="", help="Optional LoRA adapter directory")
    ap.add_argument("--max-new-tokens", type=int, default=192)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top-p", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="Limit number of rows (0 => all)")
    ap.add_argument(
        "--oracle",
        action="store_true",
        help="Use row.output/row.response as prediction (no model load). Useful for E2E smoke.",
    )
    ap.add_argument(
        "--ssot-profiles-json",
        default=str(DEFAULT_SSOT_PROFILES),
        help="LoRA profile SSOT JSON (used with --ssot-profile-key)",
    )
    ap.add_argument(
        "--ssot-profile-key",
        default="",
        help="Profile key in SSOT profiles (e.g. qwen_safe). When set, overrides --model-name from SSOT model_id.",
    )
    ap.add_argument(
        "--emit-timing",
        action="store_true",
        help="Write latency stats JSON next to predictions (stem_timing.json).",
    )
    ap.add_argument(
        "--timing-out",
        default="",
        help="Explicit timing JSON path (default: <predictions_stem>_timing.json).",
    )
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    output_path = _as_abs(args.output_path)
    ssot_path = _as_abs(args.ssot_profiles_json) if args.ssot_profiles_json else None
    if not args.oracle:
        resolved_model, ssot_used = _resolve_model_from_ssot(
            args.model_name,
            ssot_path,
            args.ssot_profile_key.strip() or None,
        )
        if ssot_used:
            print(f"model_name resolved from SSOT key={args.ssot_profile_key}: {resolved_model}")
    else:
        resolved_model = args.model_name
        ssot_used = False
    if not input_path.is_file():
        print(f"input not found: {input_path}")
        return 1

    rows = _load_jsonl(input_path)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("no rows to infer")
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    latencies_ms: list[float] = []

    timing_out_path = (
        _as_abs(args.timing_out)
        if args.timing_out.strip()
        else output_path.with_name(output_path.stem + "_timing.json")
    )

    if args.oracle:
        with output_path.open("w", encoding="utf-8") as f:
            for i, row in enumerate(rows, start=1):
                t0 = time.perf_counter()
                rid = _row_id(row, i)
                pred = str(row.get("output") or row.get("response") or "")
                f.write(json.dumps({"id": rid, "prediction": pred}, ensure_ascii=False))
                f.write("\n")
                written += 1
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        print(f"mode=oracle rows={written}")
        print(f"out={output_path}")
        if args.emit_timing:
            timing_doc = {
                "schema": "mkm_control_integrity_inference_timing_v1",
                "mode": "oracle",
                "predictions_path": str(output_path),
                "stats_ms": _percentiles_ms(latencies_ms),
            }
            timing_out_path.parent.mkdir(parents=True, exist_ok=True)
            timing_out_path.write_text(json.dumps(timing_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"timing_out={timing_out_path}")
        return 0

    model, tokenizer = _load_model_and_tokenizer(resolved_model, args.adapter_path)
    with output_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows, start=1):
            rid = _row_id(row, i)
            instruction = str(row.get("instruction", "")).strip()
            t0 = time.perf_counter()
            if not instruction:
                prediction = ""
            else:
                prediction = _generate_one(
                    model=model,
                    tokenizer=tokenizer,
                    instruction=instruction,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            f.write(json.dumps({"id": rid, "prediction": prediction}, ensure_ascii=False))
            f.write("\n")
            written += 1

    print(f"mode=model rows={written}")
    print(f"model={resolved_model}")
    print(f"out={output_path}")
    if args.emit_timing:
        timing_doc = {
            "schema": "mkm_control_integrity_inference_timing_v1",
            "mode": "model",
            "model_name": resolved_model,
            "predictions_path": str(output_path),
            "stats_ms": _percentiles_ms(latencies_ms),
        }
        timing_out_path.parent.mkdir(parents=True, exist_ok=True)
        timing_out_path.write_text(json.dumps(timing_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"timing_out={timing_out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
