#!/usr/bin/env python3
"""LoRA smoke / plan for Nemotron private lane — no 30B load by default.

--dry-run (default): emit adapter config template + dependency check only.
--check-deps: verify peft/transformers importable.
Does NOT call kaggle competitions submit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SLUG = "nvidia-nemotron-model-reasoning-challenge"
DEFAULT_BASE_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
MAX_LORA_RANK = 32


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _check_deps() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mod in ("torch", "transformers", "peft", "pandas"):
        try:
            m = __import__(mod)
            out[mod] = {"ok": True, "version": getattr(m, "__version__", None)}
        except Exception as exc:
            out[mod] = {"ok": False, "error": str(exc)}
    if out.get("torch", {}).get("ok"):
        import torch

        out["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            out["cuda_device"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            out["cuda_total_vram_gb"] = round(props.total_memory / (1024**3), 2)
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Nemotron private LoRA smoke (dry-run default).")
    p.add_argument("--slug", default=DEFAULT_SLUG)
    p.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--prep-report", type=Path, default=Path("reports/kaggle_nemotron_private_prep_latest.json"))
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("reports/kaggle_nemotron_private_lora_smoke_latest.json"),
    )
    p.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    p.add_argument("--lora-rank", type=int, default=16)
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Default: plan only, no model weights loaded.",
    )
    p.add_argument(
        "--attempt-load-tokenizer",
        action="store_true",
        help="Optional HF tokenizer probe (network); skipped by default.",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.lora_rank > MAX_LORA_RANK:
        print(f"[ERROR] lora-rank must be <= {MAX_LORA_RANK}", file=sys.stderr)
        return 1

    root = args.workspace_root
    prep_path = args.prep_report if args.prep_report.is_absolute() else root / args.prep_report
    prep: dict[str, Any] | None = None
    if prep_path.is_file():
        prep = json.loads(prep_path.read_text(encoding="utf-8"))

    deps = _check_deps()
    sft_rel = None
    if prep:
        sft_rel = (prep.get("outputs") or {}).get("sft_train_jsonl")

    lora_config = {
        "peft_type": "LORA",
        "r": args.lora_rank,
        "lora_alpha": args.lora_rank * 2,
        "lora_dropout": 0.05,
        "bias": "none",
        "task_type": "CAUSAL_LM",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    }

    report: dict[str, Any] = {
        "schema": "kaggle_nemotron_private_lora_smoke_v1",
        "generated_at_utc": _now_utc_iso(),
        "lane": "private_dev_no_mkm_core",
        "competition_slug": args.slug,
        "dry_run": args.dry_run,
        "base_model_hf_id": args.base_model,
        "lora_config_template": lora_config,
        "dependencies": deps,
        "prep_report_path": str(prep_path.relative_to(root)).replace("\\", "/") if prep_path.is_file() else None,
        "sft_jsonl": sft_rel,
        "submit_allowed_by_policy": False,
        "hardware_note": (
            "RTX 5060 Ti 16GB cannot full-finetune 30B; use Kaggle Notebook GPU or Azure NC "
            "for real adapter training. Local dry-run validates pipeline only."
        ),
        "mkm_core_exposed": False,
    }

    tokenizer_probe: dict[str, Any] = {"attempted": False}
    if args.attempt_load_tokenizer:
        tokenizer_probe["attempted"] = True
        try:
            from transformers import AutoTokenizer

            tok = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
            tokenizer_probe["ok"] = True
            tokenizer_probe["vocab_size"] = getattr(tok, "vocab_size", None)
        except Exception as exc:
            tokenizer_probe["ok"] = False
            tokenizer_probe["error"] = str(exc)
    report["tokenizer_probe"] = tokenizer_probe

    out_path = args.out_json if args.out_json.is_absolute() else root / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if not deps.get("torch", {}).get("ok"):
        print("[ERROR] torch not available", file=sys.stderr)
        return 1

    print(f"[OK] wrote: {out_path}")
    print(f"[SUMMARY] dry_run={args.dry_run} cuda={deps.get('cuda_available')} lora_r={args.lora_rank}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
