#!/usr/bin/env python3
"""DeepNSM HF 1B checkpoint — upstream baartmar/DeepNSM-1B explication + gematria index [HYPO]."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

from scripts.deepnsm_shadow_explication_lib_v1 import (
    build_translit_index,
    load_gematria_rows,
    resolve_probe_via_gematria,
)

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_CHECKPOINT = "baartmar/DeepNSM-1B"
DEFAULT_BASE = "meta-llama/Llama-3.2-1B"

_MODEL_CACHE: dict[str, Any] = {}


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=True)
    except ImportError:
        pass


def checkpoint_model_id(override: str | None = None) -> str:
    _load_dotenv()
    if override:
        return override
    return os.getenv("MKM_DEEPNSM_HF_CHECKPOINT_MODEL") or DEFAULT_CHECKPOINT


def checkpoint_base_model(override: str | None = None) -> str:
    _load_dotenv()
    if override:
        return override
    return os.getenv("MKM_DEEPNSM_HF_CHECKPOINT_BASE") or DEFAULT_BASE


def cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def build_checkpoint_prompt(sample: dict[str, Any]) -> str:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    word = str(sample.get("prime_en") or "").strip()
    en = str(lang.get("en") or word).strip()
    examples = [x for x in (en, word) if x]
    if not examples:
        examples = [word or "unknown"]
    unique_examples: list[str] = []
    for ex in examples:
        if ex not in unique_examples:
            unique_examples.append(ex)
    return f"Word: {word}\nExamples:\n" + "\n".join(unique_examples) + "\nParaphrase:\n"


def _ensure_hf_login() -> None:
    _load_dotenv()
    token = os.getenv("HF_TOKEN") or os.getenv("HF_ACCESS_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    if not token:
        return
    try:
        from huggingface_hub import login

        login(token=token, add_to_git_credential=False)
    except Exception:
        pass


def load_deepnsm_checkpoint(
    *,
    checkpoint: str | None = None,
    base_model: str | None = None,
) -> tuple[Any, Any, str, str]:
    """Load merged DeepNSM-1B (LoRA on Llama 3.2 1B). Cached per process."""
    ckpt = checkpoint_model_id(checkpoint)
    base = checkpoint_base_model(base_model)
    cache_key = f"{ckpt}::{base}"
    if cache_key in _MODEL_CACHE:
        bundle = _MODEL_CACHE[cache_key]
        return bundle["model"], bundle["tokenizer"], ckpt, base

    if not cuda_available():
        raise SystemExit("cuda_unavailable_for_deepnsm_checkpoint")

    import logging
    import warnings

    import torch
    from peft import PeftModelForCausalLM
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _ensure_hf_login()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

        major, _ = torch.cuda.get_device_capability()
        dtype = torch.bfloat16 if major >= 8 else torch.float16

        tokenizer = AutoTokenizer.from_pretrained(ckpt)
        model = AutoModelForCausalLM.from_pretrained(
            base,
            torch_dtype=dtype,
            device_map="auto",
        )
        model.resize_token_embeddings(len(tokenizer))
        model = PeftModelForCausalLM.from_pretrained(model, ckpt)
        model = model.merge_and_unload()
        model.eval()

    _MODEL_CACHE[cache_key] = {"model": model, "tokenizer": tokenizer}
    return model, tokenizer, ckpt, base


def generate_checkpoint_explication(
    sample: dict[str, Any],
    *,
    model: Any,
    tokenizer: Any,
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    prompt = build_checkpoint_prompt(sample)
    import torch

    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    input_length = inputs["input_ids"].shape[1]

    t0 = time.perf_counter()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
        )
    latency = time.perf_counter() - t0
    new_tokens = output_ids[0][input_length:]
    decoded = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return {
        "ok": bool(decoded),
        "explication": decoded[:500],
        "latency_sec": round(latency, 4),
        "prompt_preview": prompt[:200],
    }


def _hint_tokens(text: str) -> str:
    cleaned = re.sub(r"[^\w\s'-]", " ", text.lower())
    return " ".join(cleaned.split()[:40])


def fetch_checkpoint_gloss_hints(
    sample: dict[str, Any],
    *,
    model: Any,
    tokenizer: Any,
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    try:
        gen = generate_checkpoint_explication(
            sample,
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=max_new_tokens,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200], "latency_sec": None}
    if not gen.get("ok"):
        return {"ok": False, "error": "empty_explication", "latency_sec": gen.get("latency_sec")}
    excerpt = _hint_tokens(str(gen.get("explication") or ""))
    return {
        "ok": True,
        "latency_sec": gen.get("latency_sec"),
        "greek_gloss_en": excerpt[:200],
        "hebrew_gloss_en": excerpt[:200],
        "explication_preview": str(gen.get("explication") or "")[:300],
    }


def resolve_probe_via_checkpoint_assist(
    probe: str,
    lang: str,
    index: dict[tuple[str, str], list[dict[str, Any]]],
    rows: tuple[dict[str, Any], ...],
    *,
    checkpoint_hints: dict[str, Any],
    prime_en: str = "",
    en_hint: str = "",
) -> dict[str, Any]:
    lang_key = str(lang or "").strip().lower()
    gloss_key = f"{lang_key}_gloss_en"
    gloss = str(checkpoint_hints.get(gloss_key) or "")
    explication = str(checkpoint_hints.get("explication_preview") or "")
    combined_hint = " ".join(x for x in (en_hint, gloss, explication, prime_en) if x).strip()
    resolved = resolve_probe_via_gematria(probe, lang_key, index, rows, en_hint=combined_hint)
    resolved["resolution_backend"] = "deepnsm_hf_checkpoint_v1"
    resolved["checkpoint_gloss_hint"] = gloss[:120] if gloss else ""
    if resolved.get("resolution", "").startswith("gematria"):
        resolved["resolution"] = resolved["resolution"].replace("gematria", "checkpoint_assist", 1)
    return resolved


def build_hf_checkpoint_explication_record(
    sample: dict[str, Any],
    *,
    pair_index: int,
    rows: tuple[dict[str, Any], ...],
    index: dict[tuple[str, str], list[dict[str, Any]]],
    checkpoint_hints: dict[str, Any],
    checkpoint_model: str,
    base_model: str,
) -> dict[str, Any]:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    prime_en = str(sample.get("prime_en") or "")
    en_hint = str(lang.get("en") or prime_en or "")
    greek = resolve_probe_via_checkpoint_assist(
        str(lang.get("greek") or ""),
        "greek",
        index,
        rows,
        checkpoint_hints=checkpoint_hints,
        prime_en=prime_en,
        en_hint=en_hint,
    )
    hebrew = resolve_probe_via_checkpoint_assist(
        str(lang.get("hebrew") or ""),
        "hebrew",
        index,
        rows,
        checkpoint_hints=checkpoint_hints,
        prime_en=prime_en,
        en_hint=en_hint,
    )
    explication = (
        f"[HYPO][DEEPNSM_HF] NSM prime '{prime_en}' — greek→"
        f"{greek.get('lemma_script') or greek.get('resolution')} "
        f"(strongs={greek.get('strongs') or 'n/a'}); hebrew→"
        f"{hebrew.get('lemma_script') or hebrew.get('resolution')} "
        f"(strongs={hebrew.get('strongs') or 'n/a'}). checkpoint={checkpoint_model}"
    )
    return {
        "schema": "deepnsm_hf_explication_checkpoint_v1",
        "pair_index": pair_index,
        "pair_id": f"{prime_en}::{sample.get('variant') or pair_index}",
        "prime_en": prime_en,
        "variant": sample.get("variant"),
        "control": sample.get("control"),
        "lang_probes": lang,
        "checkpoint_hints": {
            "greek_gloss_en": checkpoint_hints.get("greek_gloss_en"),
            "hebrew_gloss_en": checkpoint_hints.get("hebrew_gloss_en"),
            "explication_preview": checkpoint_hints.get("explication_preview"),
            "latency_sec": checkpoint_hints.get("latency_sec"),
            "ok": checkpoint_hints.get("ok"),
        },
        "resolved_probes": {"greek": greek, "hebrew": hebrew},
        "explication_template": explication,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "implementation_note": f"Upstream DeepNSM HF checkpoint {checkpoint_model} (base {base_model}) + gematria index",
    }


def prepare_gematria_index(lexicon_path: str) -> tuple[tuple[dict[str, Any], ...], dict[tuple[str, str], list[dict[str, Any]]]]:
    rows = load_gematria_rows(lexicon_path)
    return rows, build_translit_index(rows)


__all__ = [
    "checkpoint_model_id",
    "checkpoint_base_model",
    "cuda_available",
    "build_checkpoint_prompt",
    "load_deepnsm_checkpoint",
    "generate_checkpoint_explication",
    "fetch_checkpoint_gloss_hints",
    "build_hf_checkpoint_explication_record",
    "prepare_gematria_index",
    "resolve_probe_via_checkpoint_assist",
]
