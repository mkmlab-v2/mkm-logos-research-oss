#!/usr/bin/env python3
"""LoRA SFT skeleton using Unsloth + TRL SFTTrainer (B-track research; optional GPU).

Requires (install in the environment that will run training):
  pip install unsloth transformers datasets trl peft accelerate bitsandbytes

TRL 0.24+ uses SFTConfig / processing_class (not tokenizer= on SFTTrainer).

Default base: unsloth/Qwen2.5-7B-Instruct-bnb-4bit (~16–24GB VRAM with 4bit).

Use --dry-run to verify imports, dataset load, and model load without training.
Adapter output: models/adapters/macro_prophecy_lora_v1 (gitignored under models/**)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "training" / "macro_prophecy_dataset_v1.jsonl"
DEFAULT_OUT = ROOT / "models" / "adapters" / "macro_prophecy_lora_v1"


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--model-name",
        default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        help="Hugging Face id (Unsloth 4bit preset recommended for local 24GB).",
    )
    ap.add_argument("--max-seq-length", type=int, default=2048)
    ap.add_argument("--max-steps", type=int, default=10, help="Short default for smoke; increase for real runs.")
    ap.add_argument("--learning-rate", type=float, default=2e-4)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=4, dest="grad_accum")
    ap.add_argument("--lora-r", type=int, default=16, dest="lora_r")
    ap.add_argument("--lora-alpha", type=int, default=16, dest="lora_alpha")
    ap.add_argument("--lora-dropout", type=float, default=0.0, dest="lora_dropout")
    ap.add_argument("--dataset-num-proc", type=int, default=1, dest="dataset_num_proc")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only verify JSONL rows (instruction/output); no ML imports (safe in CI / CPU-only).",
    )
    ap.add_argument(
        "--check-imports",
        action="store_true",
        help="After dataset check, try importing unsloth/torch (may be slow or fail if stack mismatched).",
    )
    ap.add_argument(
        "--smoke-load-model",
        action="store_true",
        help="With --dry-run, also load 4bit base model once (needs GPU/VRAM; optional).",
    )
    ns = ap.parse_args()

    if not ns.dataset_path.is_file():
        _die(f"missing dataset: {ns.dataset_path}\nRun: py scripts/export_general_prophecy_to_jsonl.py")

    raw_lines = [ln for ln in ns.dataset_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not raw_lines:
        _die("dataset JSONL is empty")

    import json as _json

    for i, ln in enumerate(raw_lines, 1):
        try:
            obj = _json.loads(ln)
        except _json.JSONDecodeError as e:
            _die(f"line {i}: invalid JSON: {e}")
        if "instruction" not in obj or "output" not in obj:
            _die(f"line {i}: expected instruction and output keys")

    if ns.dry_run and not ns.smoke_load_model:
        print(f"dry-run: dataset OK lines={len(raw_lines)} path={ns.dataset_path.resolve()}")
        print(f"output dir (training): {ns.output_dir.resolve()}")
        print(
            f"resolved: model={ns.model_name} max_seq={ns.max_seq_length} "
            f"lr={ns.learning_rate} batch={ns.batch_size} grad_accum={ns.grad_accum} "
            f"lora r={ns.lora_r} alpha={ns.lora_alpha} dropout={ns.lora_dropout}"
        )
        if ns.check_imports:
            try:
                import unsloth  # noqa: F401
            except ImportError as e:
                _die(
                    "Missing ML dependencies.\n"
                    "Install (CUDA env recommended): pip install unsloth transformers datasets trl peft "
                    "accelerate bitsandbytes torch\n"
                    f"Import error: {e}"
                )
            print("check-imports: unsloth import OK")
        else:
            print("hint: run with --check-imports to verify unsloth (optional; can be slow)")
        return 0

    try:
        import unsloth  # noqa: F401 — apply patches before trl/transformers heavy imports
        import torch  # noqa: F401
        from datasets import load_dataset
        from trl import SFTConfig, SFTTrainer
        from unsloth import FastLanguageModel
    except ImportError as e:
        _die(
            "Missing ML dependencies.\n"
            "Install (CUDA env recommended): pip install unsloth transformers datasets trl peft "
            "accelerate bitsandbytes torch\n"
            f"Import error: {e}"
        )

    ds = load_dataset("json", data_files=str(ns.dataset_path), split="train")

    def to_text(examples: dict) -> dict:
        inst = examples["instruction"]
        out = examples["output"]
        texts = []
        for i, o in zip(inst, out):
            texts.append(
                f"### Instruction:\n{i}\n### Response:\n{o}"
            )
        return {"text": texts}

    map_kw: dict = {"batched": True}
    if ns.dataset_num_proc and ns.dataset_num_proc > 1:
        map_kw["num_proc"] = ns.dataset_num_proc
    ds = ds.map(to_text, **map_kw)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ns.model_name,
        max_seq_length=ns.max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=ns.lora_r,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=ns.lora_alpha,
        lora_dropout=ns.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    training_args = SFTConfig(
        output_dir=str(ns.output_dir),
        max_steps=ns.max_steps,
        per_device_train_batch_size=ns.batch_size,
        gradient_accumulation_steps=ns.grad_accum,
        learning_rate=ns.learning_rate,
        logging_steps=1,
        save_steps=max(1, ns.max_steps),
        warmup_steps=1,
        report_to="none",
        dataset_text_field="text",
        max_length=ns.max_seq_length,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=ds,
        args=training_args,
    )

    if ns.dry_run and ns.smoke_load_model:
        print("dry-run + smoke-load-model: model OK; skipping trainer.train()")
        print(f"would write adapters to: {ns.output_dir.resolve()}")
        return 0

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.train()
    model.save_pretrained(str(ns.output_dir))
    tokenizer.save_pretrained(str(ns.output_dir))
    print(f"saved: {ns.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
