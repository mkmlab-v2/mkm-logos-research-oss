#!/usr/bin/env python3
"""Local inference smoke for Kaggle v28 fast LoRA adapter ([HYPO] research_only)."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "reports/kaggle_nemotron_smoke_artifact_v1/submission_v28_fast_smoke.zip"
DEFAULT_OUT = ROOT / "reports/nemotron_v28_adapter_inference_smoke_v1_latest.json"
DEFAULT_PROMPT = "Explain in one sentence why LoRA fine-tuning saves GPU memory."


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_adapter(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)


def _local_infer(
    adapter_dir: Path,
    *,
    base_model: str,
    prompt: str,
    max_new_tokens: int,
) -> tuple[str, str, float]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"[infer] base={base_model} device={device}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=dtype,
    )
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model.to(device)
    model.eval()

    messages = [{"role": "user", "content": prompt}]
    if hasattr(tokenizer, "apply_chat_template"):
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = prompt

    inputs = tokenizer(text, return_tensors="pt").to(device)
    t0 = time.perf_counter()
    with torch.no_grad():
        out_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    full = tokenizer.decode(out_ids[0], skip_special_tokens=True)
    response = full[len(text) :].strip() if full.startswith(text) else full.strip()
    return response, device, elapsed_ms


def _nim_proxy_infer(*, base_model: str, prompt: str, max_tokens: int) -> tuple[str, str, float, list[dict]]:
    import os
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    try:
        from dotenv import load_dotenv

        env_path = root / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass
    from scripts.nvidia_nim_common_v1 import api_key, chat_with_fallback

    key = api_key()
    if not key:
        raise RuntimeError("missing NVIDIA_API_KEY for nim proxy infer")
    registry_path = root / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    nim_prompt = (
        f"[HYPO] research_only. LoRA adapter trained on {base_model} is NOT loaded on NIM; "
        f"answer as cloud proxy infer only.\n\nUser: {prompt}"
    )
    t0 = time.perf_counter()
    chat, attempts = chat_with_fallback(key, registry, nim_prompt, max_tokens)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    if not chat.get("ok"):
        raise RuntimeError(chat.get("error") or "nim_proxy_infer_failed")
    model = chat.get("model") or "nim"
    return (chat.get("text") or "").strip(), f"nim:{model}", elapsed_ms, attempts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter-zip", type=Path, default=DEFAULT_ZIP)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument(
        "--mode",
        choices=("auto", "local", "nim"),
        default="auto",
        help="auto=cuda LoRA else NIM proxy; local=LoRA only; nim=cloud proxy only",
    )
    args = ap.parse_args()

    if not args.adapter_zip.is_file():
        print(f"[ERROR] missing adapter zip: {args.adapter_zip}", flush=True)
        return 1

    with tempfile.TemporaryDirectory(prefix="nemotron_v28_adapter_") as tmp:
        adapter_dir = Path(tmp)
        _extract_adapter(args.adapter_zip, adapter_dir)
        cfg_path = adapter_dir / "adapter_config.json"
        if not cfg_path.is_file():
            print("[ERROR] adapter_config.json missing in zip", flush=True)
            return 1
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        base_model = cfg.get("base_model_name_or_path") or "HuggingFaceTB/SmolLM2-360M-Instruct"

        infer_mode = args.mode
        model_attempts: list[dict] = []
        if infer_mode == "auto":
            import torch

            infer_mode = "local" if torch.cuda.is_available() else "nim"
            print(f"[infer] auto -> {infer_mode}", flush=True)

        if infer_mode == "local":
            try:
                response, device, elapsed_ms = _local_infer(
                    adapter_dir,
                    base_model=base_model,
                    prompt=args.prompt,
                    max_new_tokens=args.max_new_tokens,
                )
            except Exception as e:
                if args.mode != "auto":
                    raise
                print(f"[infer] local failed ({e}); falling back to nim", flush=True)
                infer_mode = "nim"
                response, device, elapsed_ms, model_attempts = _nim_proxy_infer(
                    base_model=base_model,
                    prompt=args.prompt,
                    max_tokens=args.max_new_tokens,
                )
        else:
            response, device, elapsed_ms, model_attempts = _nim_proxy_infer(
                base_model=base_model,
                prompt=args.prompt,
                max_tokens=args.max_new_tokens,
            )

        doc = {
            "schema": "nemotron_v28_adapter_inference_smoke_v1",
            "finished_at_utc": _utc(),
            "lane": "research_only",
            "research_only": True,
            "wired_into_train": False,
            "track_wall": "no_track_a_live_auto_merge",
            "infer_mode": infer_mode,
            "adapter_zip": str(args.adapter_zip),
            "base_model": base_model,
            "device": device,
            "model_attempts": model_attempts or None,
            "prompt": args.prompt,
            "response_preview": response[:500],
            "response_chars": len(response),
            "elapsed_ms": elapsed_ms,
            "status": "pass" if response else "empty_response",
            "nim_proxy_note": (
                "LoRA weights not applied on NIM; cloud base-model proxy only"
                if str(device).startswith("nim:")
                else None
            ),
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[OK] response_chars={len(response)} elapsed_ms={elapsed_ms}", flush=True)
        print(response[:400], flush=True)
        print(f"[OK] {args.out_json}", flush=True)
        return 0 if response else 2


if __name__ == "__main__":
    raise SystemExit(main())
