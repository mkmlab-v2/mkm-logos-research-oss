#!/usr/bin/env python3
"""Verify RunPod-pulled Nemotron LoRA adapter on disk (no full model load)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    adapter = root / "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/output"
    required = ["adapter_config.json", "adapter_model.safetensors"]
    for name in required:
        path = adapter / name
        if not path.is_file():
            print(f"[ERROR] missing {path}", file=sys.stderr)
            return 1
        print(f"[ok] {name} bytes={path.stat().st_size}")

    cfg = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    print(
        f"[ok] peft_type={cfg.get('peft_type')} r={cfg.get('r')} "
        f"base={cfg.get('base_model_name_or_path')}"
    )

    try:
        from safetensors import safe_open

        with safe_open(adapter / "adapter_model.safetensors", framework="pt") as f:
            keys = list(f.keys())
        print(f"[ok] safetensors tensors={len(keys)} sample={keys[:3]}")
    except ImportError:
        print("[warn] safetensors not installed — skipped tensor key scan")

    out = root / "reports/nemotron_pulled_adapter_verify_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "nemotron_pulled_adapter_verify_v1",
        "lane": "research_only",
        "adapter_dir": str(adapter),
        "adapter_config": cfg,
        "tensor_count": len(keys) if "keys" in dir() else None,
        "status": "ok",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
