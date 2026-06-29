#!/usr/bin/env python3
"""Harness step 1: read disk SSOT before asking the commander (no secrets in output).

Reproducible:
  py scripts/invoke_mkm_harness_read_ssot_v1.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bigset_free_tier_profile_v1 import (  # noqa: E402
    azure_credentials_present,
    load_dotenv_quiet,
)

CENTRAL = ROOT / "docs/final/CENTRAL_AGENT_MEMORY_V1.md"
ENV_PATH = ROOT / ".env"
BIGSET_PROFILE_ART = ROOT / "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/mkm_harness_read_ssot_v1_latest.json"

ENV_KEY_NAMES = (
    "MKM_LLM_PRIORITY",
    "BIGSET_LLM_PROFILE",
    "BIGSET_OLLAMA_MODEL",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_SUBSCRIPTION_NAME",
    "AZURE_STARTUP_CREDITS_USD_REMAINING",
    "AZURE_STARTUP_CREDITS_EXPIRE",
    "OPENROUTER_API_KEY",
    "TINYFISH_API_KEY",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_key_presence() -> dict[str, bool]:
    load_dotenv_quiet()
    out: dict[str, bool] = {}
    if not ENV_PATH.is_file():
        return {k: False for k in ENV_KEY_NAMES}
    text = ENV_PATH.read_text(encoding="utf-8", errors="ignore")
    for name in ENV_KEY_NAMES:
        pat = re.compile(rf"^\s*{re.escape(name)}\s*=\s*\S+", re.MULTILINE)
        out[name] = bool(pat.search(text)) or bool((os.environ.get(name) or "").strip())
    return out


def _central_checkpoint_tail() -> list[str]:
    if not CENTRAL.is_file():
        return []
    block = CENTRAL.read_text(encoding="utf-8", errors="ignore")
    lines = []
    for line in block.splitlines():
        if line.strip().startswith("- **20") and "—" in line:
            lines.append(line.strip().lstrip("- ").strip())
    return lines[:5]


def main() -> int:
    keys = _env_key_presence()
    azure_ok = azure_credentials_present()
    bigset_profile = None
    if BIGSET_PROFILE_ART.is_file():
        try:
            bigset_profile = json.loads(BIGSET_PROFILE_ART.read_text(encoding="utf-8")).get("applied")
        except json.JSONDecodeError:
            bigset_profile = None

    never_ask = []
    if azure_ok:
        never_ask.append("azure_openai_endpoint_deployment_key")
    if keys.get("TINYFISH_API_KEY"):
        never_ask.append("tinyfish_api_key")
    if keys.get("OPENROUTER_API_KEY"):
        never_ask.append("openrouter_api_key")

    doc = {
        "schema": "mkm_harness_read_ssot_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": True,
        "env_key_presence": keys,
        "azure_openai_configured": azure_ok,
        "mkm_llm_priority": (os.environ.get("MKM_LLM_PRIORITY") or "").strip() or None,
        "bigset_llm_profile": (os.environ.get("BIGSET_LLM_PROFILE") or "").strip() or None,
        "bigset_profile_artifact": bigset_profile,
        "central_checkpoint_tail": _central_checkpoint_tail(),
        "agent_never_reask_if_present": never_ask,
        "reproduce": "py scripts/invoke_mkm_harness_read_ssot_v1.py",
        "next_harness_steps": [
            "py scripts/mkm_intent_router_local_v1.py --query \"<user question>\"",
            "powershell -File scripts\\Invoke-BigSetAzureStart_v1.ps1",
            "py scripts/run_bigset_logos_fusion_chain_v1.py --live --auto-setup --free-tier --free-tier-mode azure",
        ],
    }
    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifact": str(OUT_ART.relative_to(ROOT)), "azure_ok": azure_ok}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
