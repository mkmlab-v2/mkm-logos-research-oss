"""Nemotron hybrid QLoRA: bnb skip-module contract (mamba fused path)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/nemotron_qlora_train_v1.py"


def _load_train():
    spec = importlib.util.spec_from_file_location("nemotron_qlora_train_v1", TRAIN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bnb_modules_to_not_convert_nemotron_includes_out_proj() -> None:
    mod = _load_train()
    skip = mod._bnb_modules_to_not_convert("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16")
    assert "out_proj" in skip
    assert "lm_head" in skip
    src = (TRAIN).read_text(encoding="utf-8")
    assert "llm_int8_skip_modules=skip_modules" in src


def test_bnb_modules_to_not_convert_generic_lm_head_only() -> None:
    mod = _load_train()
    skip = mod._bnb_modules_to_not_convert("meta-llama/Llama-3.2-1B")
    assert skip == ["lm_head"]
