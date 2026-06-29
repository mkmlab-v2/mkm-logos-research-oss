#!/usr/bin/env python3
"""Prereq check for DeepNSM HF 1B checkpoint inference [HYPO]."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/deepnsm_hf_checkpoint_prereqs_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_hf_token() -> str:
    for key in ("HF_TOKEN", "HF_ACCESS_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        val = os.getenv(key, "").strip()
        if val:
            return val
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("HF_TOKEN="):
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--require-cuda", action="store_true", default=True)
    args = ap.parse_args()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from scripts.deepnsm_hf_checkpoint_inference_lib_v1 import (
        checkpoint_base_model,
        checkpoint_model_id,
        cuda_available,
    )

    checks: dict[str, dict] = {}
    try:
        import torch  # noqa: F401

        checks["torch"] = {"ok": True}
    except ImportError:
        checks["torch"] = {"ok": False, "error": "missing_torch"}

    for pkg in ("transformers", "peft", "accelerate"):
        try:
            __import__(pkg)
            checks[pkg] = {"ok": True}
        except ImportError:
            checks[pkg] = {"ok": False, "error": f"missing_{pkg}"}

    cuda_ok = cuda_available()
    checks["cuda"] = {"ok": cuda_ok}
    hf_token = _load_hf_token()
    checks["hf_token"] = {"ok": bool(hf_token), "note": "optional_for_public_models"}

    ckpt = checkpoint_model_id()
    base = checkpoint_base_model()
    hub_ok = False
    hub_error = ""
    if checks.get("transformers", {}).get("ok"):
        try:
            from huggingface_hub import model_info

            model_info(ckpt, token=hf_token or None)
            model_info(base, token=hf_token or None)
            hub_ok = True
        except Exception as exc:
            hub_error = str(exc)[:200]

    checks["hf_hub_reachable"] = {"ok": hub_ok, "checkpoint": ckpt, "base": base, "error": hub_error or None}

    llama_gate_ok = False
    llama_gate_error = ""
    if hf_token:
        try:
            from huggingface_hub import hf_hub_download

            hf_hub_download(base, "config.json", token=hf_token)
            llama_gate_ok = True
        except Exception as exc:
            llama_gate_error = str(exc)[:300]
    else:
        llama_gate_error = "missing_hf_token_for_gated_llama_base"

    checks["llama_base_gate"] = {
        "ok": llama_gate_ok,
        "base_model": base,
        "accept_url": f"https://huggingface.co/{base}",
        "error": llama_gate_error or None,
    }

    core_ok = all(checks[k]["ok"] for k in ("torch", "transformers", "peft", "accelerate"))
    ok = core_ok and (cuda_ok or not args.require_cuda) and hub_ok and llama_gate_ok

    doc = {
        "schema": "deepnsm_hf_checkpoint_prereqs_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "checkpoint_model": ckpt,
        "base_model": base,
        "ok": ok,
        "checks": checks,
        "reproduce": "py scripts/check_deepnsm_hf_checkpoint_prereqs_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out),
                "cuda": cuda_ok,
                "hub_ok": hub_ok,
                "llama_gate_ok": llama_gate_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
