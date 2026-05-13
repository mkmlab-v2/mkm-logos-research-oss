#!/usr/bin/env python3
"""Pack 0-B: batch inference + golden alignment eval for myeongri deterministic LoRA.

Loads golden JSONL (expected_result), builds the same instruction string as
convert_myeongri_golden_to_sft_instruction_jsonl_v1.py, runs the base model +
optional PEFT adapter, parses JSON from the model output, and compares to
expected_result (normalized: drops calculated_at under full_saju if present).

Exit codes:
  0 — completed; alignment_pass_rate in report (may be 0.0)
  1 — bad args / missing files
  2 — no rows after filters
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLDEN = WORKSPACE_ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
DEFAULT_PROFILE_JSON = (
    WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "myeongri_deterministic_lora_model_profiles_v1.json"
)
DEFAULT_PREDICTIONS = WORKSPACE_ROOT / "reports" / "myeongri_deterministic_lora_predictions_latest.jsonl"
DEFAULT_REPORT = WORKSPACE_ROOT / "reports" / "myeongri_deterministic_lora_inference_eval_latest.json"


def _as_abs(path_str: str | Path) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
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


def _instruction_from_golden_row(row: dict[str, Any]) -> str:
    """Mirror scripts/convert_myeongri_golden_to_sft_instruction_jsonl_v1._row_to_sft instruction."""
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    return (
        "Deterministic myeongri task. Given birth_instant_utc, iana_tz, is_male, "
        "emit ONLY valid JSON for schema saju_global_birth_result_v1 "
        "(fields: schema, version, resolution, full_saju; omit calculated_at under full_saju).\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )


def _resolve_profile_model_id(profile_json: Path, profile_key: str) -> str:
    doc = json.loads(profile_json.read_text(encoding="utf-8"))
    prof = (doc.get("profiles") or {}).get(profile_key) or {}
    if not isinstance(prof, dict):
        raise SystemExit(f"profile key not found or invalid: {profile_key!r} in {profile_json}")
    mid = str(prof.get("model_id") or "").strip()
    if not mid:
        raise SystemExit(f"profile {profile_key!r} missing model_id in {profile_json}")
    return mid


def _resolve_quantization(profile_json: Path) -> tuple[bool, str]:
    if not profile_json.is_file():
        return False, "nf4"
    try:
        doc = json.loads(profile_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "nf4"
    q = doc.get("quantization")
    if not isinstance(q, dict):
        return False, "nf4"
    return bool(q.get("load_in_4bit", False)), str(q.get("bnb_4bit_quant_type", "nf4") or "nf4")


def _percentiles_ms(lat_ms: list[float]) -> dict[str, float]:
    if not lat_ms:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "count": 0}
    s = sorted(lat_ms)
    n = len(s)

    def pct(p: float) -> float:
        if n == 1:
            return float(s[0])
        k = (n - 1) * (p / 100.0)
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return float(s[lo] + (k - lo) * (s[hi] - s[lo]))

    return {
        "mean_ms": round(float(statistics.mean(lat_ms)), 3),
        "p50_ms": round(pct(50), 3),
        "p95_ms": round(pct(95), 3),
        "count": n,
    }


def _build_prompt(instruction: str) -> str:
    return f"### Instruction:\n{instruction}\n### Response:\n"


def _balanced_json_slice(s: str) -> str | None:
    """Return substring from first balanced `{...}` (string-aware), or None."""
    i = s.find("{")
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(s)):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[i : j + 1]
    return None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse first JSON object from model text (fences, full parse, balanced slice, string-wrapped JSON)."""
    s = (text or "").strip()
    if not s:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()

    def _loads_dict(raw: str) -> dict[str, Any] | None:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str):
            inner = obj.strip()
            if inner.startswith("{") and inner.endswith("}"):
                try:
                    inner_obj = json.loads(inner)
                except json.JSONDecodeError:
                    return None
                return inner_obj if isinstance(inner_obj, dict) else None
        return None

    for candidate in (s, _balanced_json_slice(s) or ""):
        if not candidate:
            continue
        got = _loads_dict(candidate)
        if got is not None:
            return got
    return None


def _drop_calculated_at(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {k: _drop_calculated_at(v) for k, v in obj.items() if k != "calculated_at"}
        return out
    if isinstance(obj, list):
        return [_drop_calculated_at(x) for x in obj]
    return obj


def _normalize_result(d: dict[str, Any]) -> dict[str, Any]:
    d2 = deepcopy(d)
    fs = d2.get("full_saju")
    if isinstance(fs, dict):
        d2["full_saju"] = _drop_calculated_at(fs)
    return d2


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _model_device(model: Any) -> Any:
    import torch

    try:
        dev = getattr(model, "device", None)
        if dev is not None:
            return dev
    except Exception:
        pass
    return next(model.parameters()).device


def _load_model_and_tokenizer(
    model_name: str,
    adapter_path: str,
    *,
    load_in_4bit: bool,
    bnb_4bit_quant_type: str,
):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if adapter_path and torch.cuda.is_available():
        device_map: Any = {"": 0}
    elif adapter_path:
        device_map = "cpu"
    else:
        device_map = "auto"

    model_kwargs: dict[str, Any] = {"trust_remote_code": True, "device_map": device_map}
    if load_in_4bit:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["torch_dtype"] = torch.float16

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return model, tokenizer


def _generate_one(
    model,
    tokenizer,
    instruction: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    *,
    repetition_penalty: float,
) -> str:
    import torch

    prompt = _build_prompt(instruction)
    inputs = tokenizer(prompt, return_tensors="pt")
    dev = _model_device(model)
    inputs = {k: v.to(dev) for k, v in inputs.items()}
    gen_kw: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "do_sample": temperature > 0,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token_id": tokenizer.pad_token_id,
    }
    if repetition_penalty and repetition_penalty > 1.0:
        gen_kw["repetition_penalty"] = float(repetition_penalty)
    with torch.no_grad():
        output_ids = model.generate(**inputs, **gen_kw)
    full = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    if "### Response:" in full:
        return full.split("### Response:", 1)[1].strip()
    return full.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=str, default=str(DEFAULT_GOLDEN))
    ap.add_argument("--adapter-path", default="", help="PEFT adapter directory (empty = base model only)")
    ap.add_argument("--model-name", default="", help="Base HF model id (default: --profile-key from SSOT)")
    ap.add_argument("--profile-json", type=str, default=str(DEFAULT_PROFILE_JSON))
    ap.add_argument("--profile-key", default="train_default", help="Key in profile-json for model_id default")
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top-p", type=float, default=1.0)
    ap.add_argument(
        "--repetition-penalty",
        type=float,
        default=1.15,
        help=">1.0 reduces degenerate repeats (0 disables).",
    )
    ap.add_argument("--limit", type=int, default=0, help="Max rows (0 = all)")
    ap.add_argument("--split", default="", help="If set, only rows where golden.split equals this value")
    ap.add_argument(
        "--oracle-golden",
        action="store_true",
        help="Skip model; use json.dumps(expected_result) as prediction (pipeline smoke).",
    )
    ap.add_argument("--predictions-jsonl", type=str, default=str(DEFAULT_PREDICTIONS))
    ap.add_argument("--report-json", type=str, default=str(DEFAULT_REPORT))
    ap.add_argument("--emit-timing", action="store_true")
    args = ap.parse_args()

    golden_path = _as_abs(args.golden_jsonl)
    profile_json = _as_abs(args.profile_json)
    pred_path = _as_abs(args.predictions_jsonl)
    report_path = _as_abs(args.report_json)

    if not golden_path.is_file():
        print(f"missing golden jsonl: {golden_path}", file=sys.stderr)
        return 1

    model_name = str(args.model_name or "").strip()
    if not model_name:
        if not profile_json.is_file():
            print(f"missing profile-json for model default: {profile_json}", file=sys.stderr)
            return 1
        model_name = _resolve_profile_model_id(profile_json, args.profile_key)

    adapter_path = str(args.adapter_path or "").strip()
    if not args.oracle_golden and adapter_path:
        apath = _as_abs(adapter_path)
        if not apath.is_dir():
            print(f"adapter path not found: {apath}", file=sys.stderr)
            return 1
        adapter_path = str(apath)

    rows = _load_jsonl(golden_path)
    if args.split.strip():
        rows = [r for r in rows if str(r.get("split", "")) == args.split.strip()]
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("no rows after filters", file=sys.stderr)
        return 2

    load_in_4bit, bnb_qt = _resolve_quantization(profile_json)
    if args.oracle_golden:
        load_in_4bit = False
    else:
        import torch

        if load_in_4bit and not torch.cuda.is_available():
            print(
                "warn: SSOT requests load_in_4bit but CUDA is unavailable; loading fp weights on CPU.",
                file=sys.stderr,
            )
            load_in_4bit = False

    pred_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    latencies_ms: list[float] = []
    per_row: list[dict[str, Any]] = []
    parse_ok = 0
    match_ok = 0

    model = tokenizer = None
    if not args.oracle_golden:
        model, tokenizer = _load_model_and_tokenizer(
            model_name,
            adapter_path,
            load_in_4bit=load_in_4bit,
            bnb_4bit_quant_type=bnb_qt,
        )

    with pred_path.open("w", encoding="utf-8") as fout:
        for idx, row in enumerate(rows, start=1):
            sid = str(row.get("sample_id") or f"row-{idx:06d}")
            exp = row.get("expected_result")
            if not isinstance(exp, dict):
                print(f"row {sid}: missing expected_result", file=sys.stderr)
                return 1
            instruction = _instruction_from_golden_row(row)

            t0 = time.perf_counter()
            if args.oracle_golden:
                raw_pred = json.dumps(exp, ensure_ascii=False, separators=(",", ":"))
            else:
                assert model is not None and tokenizer is not None
                raw_pred = _generate_one(
                    model=model,
                    tokenizer=tokenizer,
                    instruction=instruction,
                    max_new_tokens=int(args.max_new_tokens),
                    temperature=float(args.temperature),
                    top_p=float(args.top_p),
                    repetition_penalty=float(args.repetition_penalty),
                )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            parsed = _extract_json_object(raw_pred)
            exp_n = _normalize_result(exp)
            ok_parse = parsed is not None
            ok_match = False
            mismatch_note = ""
            if ok_parse:
                pred_n = _normalize_result(parsed)
                ok_match = _canonical_json(pred_n) == _canonical_json(exp_n)
                if not ok_match:
                    mismatch_note = "canonical_json_mismatch"
            else:
                mismatch_note = "json_parse_failed"

            if ok_parse:
                parse_ok += 1
            if ok_match:
                match_ok += 1

            rec = {
                "sample_id": sid,
                "split": row.get("split"),
                "parse_ok": ok_parse,
                "exact_match_normalized": ok_match,
                "mismatch_note": mismatch_note,
                "prediction_raw_head": raw_pred[:500],
            }
            per_row.append(rec)
            fout.write(
                json.dumps(
                    {"id": sid, "prediction": raw_pred, "parse_ok": ok_parse, "exact_match": ok_match},
                    ensure_ascii=False,
                )
                + "\n"
            )

    n = len(rows)
    report = {
        "schema": "myeongri_deterministic_lora_inference_eval_v1",
        "golden_jsonl": str(golden_path),
        "max_new_tokens": int(args.max_new_tokens),
        "repetition_penalty": float(args.repetition_penalty),
        "model_name": model_name,
        "adapter_path": adapter_path or None,
        "oracle_golden": bool(args.oracle_golden),
        "profile_key": args.profile_key,
        "rows": n,
        "parse_ok": parse_ok,
        "parse_ok_rate": round(parse_ok / n, 6) if n else 0.0,
        "exact_match_normalized": match_ok,
        "alignment_pass_rate": round(match_ok / n, 6) if n else 0.0,
        "predictions_jsonl": str(pred_path),
        "per_row": per_row,
    }
    if args.emit_timing:
        report["timing_ms"] = _percentiles_ms(latencies_ms)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report_path), "alignment_pass_rate": report["alignment_pass_rate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
