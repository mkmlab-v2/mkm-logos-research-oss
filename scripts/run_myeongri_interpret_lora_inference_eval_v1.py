#!/usr/bin/env python3
"""Eval interpret-only LoRA on SFT JSONL (instruction -> envelope v1)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_interpret_envelope_views_v1 import extract_compact_from_interpret_instruction  # noqa: E402
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope  # noqa: E402

DEFAULT_SFT = ROOT / "data/training/myeongri_interpret_sft_v2/locked_eval.jsonl"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_PRED = ROOT / "reports/myeongri_interpret_lora_predictions_latest.jsonl"
DEFAULT_REPORT = ROOT / "reports/myeongri_interpret_lora_inference_eval_latest.json"


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _canonical_envelope(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_SFT)
    ap.add_argument("--adapter-path", default="")
    ap.add_argument("--model-name", default="")
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--profile-key", default="train_default")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--max-new-tokens", type=int, default=448)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument(
        "--row-indices",
        default="",
        help="Comma-separated 1-based row indices to eval (default: first --limit rows).",
    )
    ap.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PRED)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--oracle-sft", action="store_true", help="Use SFT output as prediction (smoke)")
    args = ap.parse_args()

    if not args.sft_jsonl.is_file():
        print(f"missing sft jsonl: {args.sft_jsonl}", file=sys.stderr)
        return 2

    from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import (
        _generate_one,
        _load_model_and_tokenizer,
        _resolve_profile_model_id,
        _resolve_quantization,
    )

    all_rows = _load_jsonl(args.sft_jsonl)
    if args.row_indices.strip():
        wanted_list = [int(x.strip()) for x in args.row_indices.split(",") if x.strip()]
        pairs: list[tuple[int, dict]] = []
        for i in wanted_list:
            if 1 <= i <= len(all_rows):
                pairs.append((i, all_rows[i - 1]))
        row_indices = [p[0] for p in pairs]
        rows = [p[1] for p in pairs]
    elif args.limit > 0:
        rows = all_rows[: args.limit]
        row_indices = list(range(1, len(rows) + 1))
    else:
        rows = all_rows
        row_indices = list(range(1, len(rows) + 1))
    if not rows:
        print("no rows", file=sys.stderr)
        return 2

    model_name = args.model_name.strip() or _resolve_profile_model_id(args.profile_json, args.profile_key)
    adapter = str(args.adapter_path or "").strip()
    load_in_4bit, bnb_qt = _resolve_quantization(args.profile_json)

    model = tokenizer = None
    if not args.oracle_sft:
        model, tokenizer = _load_model_and_tokenizer(
            model_name,
            adapter,
            load_in_4bit=load_in_4bit,
            bnb_4bit_quant_type=bnb_qt,
        )

    parse_ok = match_ok = coerced_ok = 0
    per_row: list[dict[str, Any]] = []
    args.predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.predictions_jsonl.open("w", encoding="utf-8") as fout:
        for idx, row in zip(row_indices, rows, strict=False):
            i = idx
            instruction = str(row.get("instruction", ""))
            gold_out = json.loads(str(row.get("output", "{}")))
            compact = extract_compact_from_interpret_instruction(instruction)
            gold_sha = str(gold_out.get("deterministic_input_sha256") or "")
            if args.oracle_sft:
                raw = row.get("output", "")
            else:
                t0 = time.perf_counter()
                raw = _generate_one(
                    model=model,
                    tokenizer=tokenizer,
                    instruction=instruction,
                    max_new_tokens=int(args.max_new_tokens),
                    temperature=float(args.temperature),
                    top_p=float(args.top_p),
                    repetition_penalty=1.15,
                    chat_leak_stop=True,
                )
                _ = time.perf_counter() - t0
            parsed, note, coerced = _try_parse_envelope(
                raw if isinstance(raw, str) else json.dumps(raw),
                gold_out=gold_out,
                postprocess_v1=True,
                compact=compact,
                lang="ko",
                deterministic_input_sha256=gold_sha,
            )
            ok_parse = parsed is not None and note == ""
            if ok_parse:
                parse_ok += 1
            if coerced:
                coerced_ok += 1
            ok_match = False
            if ok_parse and parsed is not None:
                ok_match = _canonical_envelope(parsed) == _canonical_envelope(gold_out)
                if ok_match:
                    match_ok += 1
            rec = {
                "row_index": i,
                "parse_ok": ok_parse,
                "envelope_coerced_from_template": coerced,
                "envelope_match_normalized": ok_match,
                "mismatch_note": note or None,
                "prediction_raw_head": (raw if isinstance(raw, str) else str(raw))[:400],
            }
            per_row.append(rec)
            fout.write(
                json.dumps(
                    {"row_index": i, "instruction_head": instruction[:200], "prediction_raw": raw},
                    ensure_ascii=False,
                )
                + "\n"
            )

    n = len(rows)
    sft_rel = args.sft_jsonl.resolve()
    try:
        sft_rel = sft_rel.relative_to(ROOT.resolve())
    except ValueError:
        sft_rel = args.sft_jsonl
    report = {
        "schema": "myeongri_interpret_lora_inference_eval_v1",
        "sft_jsonl": str(sft_rel).replace("\\", "/"),
        "rows": n,
        "parse_ok_rate": round(parse_ok / n, 6) if n else 0.0,
        "envelope_coerced_rate": round(coerced_ok / n, 6) if n else 0.0,
        "envelope_match_rate": round(match_ok / n, 6) if n else 0.0,
        "adapter_path": adapter or None,
        "oracle_sft": bool(args.oracle_sft),
        "per_row": per_row,
        "hypothesis_tier": "B",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "parse_ok_rate": report["parse_ok_rate"], "out": str(args.report_json)}))
    return 0 if parse_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
