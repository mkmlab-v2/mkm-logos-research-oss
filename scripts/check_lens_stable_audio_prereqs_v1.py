#!/usr/bin/env python3
"""Prereqs for Stable Audio Open lens B-track bake (HF gate + CUDA)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "stabilityai/stable-audio-open-1.0"


def _load_dotenv_hf_token() -> str | None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("HF_TOKEN="):
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            return val or None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-id", default=os.environ.get("MKM_AUDIO_STABLE_AUDIO_MODEL", DEFAULT_MODEL))
    ap.add_argument("--probe-model", action="store_true", help="Try hf_hub model_info (network)")
    args = ap.parse_args()

    report: dict = {
        "schema": "lens_stable_audio_prereqs_v1",
        "model_id": args.model_id,
        "checks": {},
    }
    ok = True

    try:
        import torch

        report["checks"]["cuda"] = bool(torch.cuda.is_available())
    except ImportError:
        report["checks"]["cuda"] = False
        ok = False

    try:
        import diffusers  # noqa: F401

        report["checks"]["diffusers"] = True
    except ImportError:
        report["checks"]["diffusers"] = False
        ok = False

    try:
        import torchsde  # noqa: F401

        report["checks"]["torchsde"] = True
    except ImportError:
        report["checks"]["torchsde"] = False
        ok = False

    token = (_load_dotenv_hf_token() or "") or os.environ.get("HF_TOKEN", "").strip()
    report["checks"]["hf_token_present"] = bool(token)

    if token:
        try:
            from huggingface_hub import HfApi

            who = HfApi(token=token).whoami()
            report["hf_account"] = {
                "name": who.get("name"),
                "type": who.get("type"),
            }
            access_tok = (who.get("auth") or {}).get("accessToken") or {}
            fine = access_tok.get("fineGrained") or {}
            can_gated = fine.get("canReadGatedRepos")
            role = access_tok.get("role")
            if can_gated is not None:
                report["checks"]["hf_token_can_read_gated"] = bool(can_gated)
                report["hf_token"] = {
                    "display_name": access_tok.get("displayName"),
                    "role": role,
                }
                if not can_gated:
                    ok = False
            elif role == "read":
                report["checks"]["hf_token_can_read_gated"] = "classic_read_assumed"
                report["hf_token"] = {"display_name": access_tok.get("displayName"), "role": role}
        except Exception as exc:
            report["hf_account"] = {"error": type(exc).__name__}

    if args.probe_model and token:
        try:
            from huggingface_hub import hf_hub_download

            hf_hub_download(args.model_id, "model_index.json", token=token)
            report["checks"]["hf_model_access"] = True
        except Exception as exc:
            report["checks"]["hf_model_access"] = False
            report["checks"]["hf_model_access_error"] = type(exc).__name__
            ok = False
    elif args.probe_model:
        report["checks"]["hf_model_access"] = False
        report["checks"]["hf_model_access_error"] = "missing_hf_token"
        ok = False

    if args.probe_model and token and not report["checks"].get("hf_model_access"):
        acct = (report.get("hf_account") or {}).get("name") or "your HF account"
        actions = [
            f"1) Log in as {acct} and Agree: https://huggingface.co/{args.model_id}",
        ]
        if report["checks"].get("hf_token_can_read_gated") is False:
            actions.append(
                "2) Regenerate HF_TOKEN with Read + gated repos: https://huggingface.co/settings/tokens"
            )
            report["checks"]["hf_model_access_error"] = report["checks"].get(
                "hf_model_access_error", "token_missing_gated_read"
            )
        report["license_action"] = " · ".join(actions)

    if not report["checks"].get("hf_token_present"):
        report["hint"] = (
            "Add HF_TOKEN to .env and accept license: "
            "https://huggingface.co/stabilityai/stable-audio-open-1.0"
        )
        ok = False

    report["ok"] = ok
    out = ROOT / "reports/lens_stable_audio_prereqs_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
