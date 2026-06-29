#!/usr/bin/env python3
"""Apply BigSet LLM profile from .env (OpenRouter :free · Ollama · Azure OpenAI).

Does not start BigSet — restart `bigset start` after apply so backend picks up env.

Reproducible:
  py scripts/apply_bigset_free_tier_profile_v1.py
  py scripts/apply_bigset_free_tier_profile_v1.py --mode ollama
  py scripts/apply_bigset_free_tier_profile_v1.py --mode azure
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bigset_free_tier_profile_v1 import (  # noqa: E402
    apply_profile_to_environ,
    azure_credentials_present,
    profile_public_snapshot,
    resolve_profile,
)

DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply BigSet free-tier model profile to process env")
    ap.add_argument("--mode", choices=["openrouter_free", "ollama", "azure"], default=None)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    mode = args.mode
    if mode == "ollama":
        mode = "ollama_local"
    elif mode == "azure":
        mode = "azure_openai"
    profile = resolve_profile(mode=mode)
    applied = apply_profile_to_environ(profile)

    has_openrouter = bool((profile.get("OPENROUTER_BASE_URL") or "").startswith("http://127.0.0.1"))
    ok = True
    warnings: list[str] = []
    if profile.get("profile_mode") == "openrouter_free":
        import os

        if not (os.environ.get("OPENROUTER_API_KEY") or "").strip():
            ok = False
            warnings.append("OPENROUTER_API_KEY missing — free models still need an API key (no card)")
    if profile.get("profile_mode") == "ollama_local":
        warnings.append("Ollama must be running; structured JSON may fail on small models")
    if profile.get("profile_mode") == "azure_openai":
        if not azure_credentials_present():
            ok = False
            warnings.append("AZURE_OPENAI_ENDPOINT/API_KEY/DEPLOYMENT missing in .env")
        else:
            warnings.append("Restart bigset after apply; uses Azure credits not personal OpenRouter card")

    doc = {
        "schema": "bigset_free_tier_profile_v1",
        "generated_at_utc": _now(),
        "ok": ok,
        "research_only": True,
        "send_gate": "HOLD",
        "applied": profile_public_snapshot(profile),
        "warnings": warnings,
        "restart_required": "Stop and re-run `bigset start` in a shell that inherits these env vars",
        "reproduce": "py scripts/apply_bigset_free_tier_profile_v1.py",
        "live_chain": "py scripts/run_bigset_logos_fusion_chain_v1.py --live --auto-setup --free-tier --free-tier-mode azure",
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "profile_mode": profile.get("profile_mode"),
                "applied_keys": list(applied.keys()),
                "artifact": str(args.artifact.relative_to(ROOT)),
                "warnings": warnings,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
