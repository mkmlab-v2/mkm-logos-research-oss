#!/usr/bin/env python3
"""Windows-safe LoRA SFT fallback (Transformers + PEFT, no Unsloth runtime).

Purpose:
- Provide a practical GPU training path when Unsloth/Triton fails on Windows.
- Keep behavior close to existing dataset contract (instruction/output JSONL).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "training" / "macro_prophecy_dataset_v1.jsonl"
DEFAULT_OUT = ROOT / "models" / "adapters" / "macro_prophecy_lora_windows_fallback_v1"


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "instruction" not in obj or "output" not in obj:
            raise ValueError(f"line {i}: expected instruction/output")
        rows.append(obj)
    return rows


def _build_dataset(rows: list[dict], tokenizer, max_len: int) -> Dataset:
    texts = [
        f"### Instruction:\n{r['instruction']}\n### Response:\n{r['output']}"
        for r in rows
    ]
    ds = Dataset.from_dict({"text": texts})

    def tok(batch):
        out = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_len,
            padding="max_length",
        )
        out["labels"] = [ids[:] for ids in out["input_ids"]]
        return out

    return ds.map(tok, batched=True, remove_columns=["text"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model-name", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--max-seq-length", type=int, default=1024)
    ap.add_argument("--max-steps", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--learning-rate", type=float, default=2e-4)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    if not ns.dataset_path.is_file():
        raise SystemExit(f"missing dataset: {ns.dataset_path}")
    rows = _load_rows(ns.dataset_path)
    if not rows:
        raise SystemExit("dataset empty")

    print(f"dataset_ok rows={len(rows)} path={ns.dataset_path}")
    print(f"cuda_available={torch.cuda.is_available()} device_count={torch.cuda.device_count()}")
    if ns.dry_run:
        return 0

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float16,
    )
    tokenizer = AutoTokenizer.from_pretrained(ns.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        ns.model_name,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=16,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    ds = _build_dataset(rows, tokenizer, ns.max_seq_length)

    args = TrainingArguments(
        output_dir=str(ns.output_dir),
        max_steps=ns.max_steps,
        per_device_train_batch_size=ns.batch_size,
        gradient_accumulation_steps=ns.grad_accum,
        learning_rate=ns.learning_rate,
        logging_steps=1,
        save_steps=max(1, ns.max_steps),
        warmup_steps=1,
        bf16=torch.cuda.is_available(),
        fp16=False,
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=args, train_dataset=ds)

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.train()
    model.save_pretrained(str(ns.output_dir))
    tokenizer.save_pretrained(str(ns.output_dir))
    print(f"saved={ns.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

