#!/usr/bin/env python3
"""Azure OpenAI smoke (native + v1 paths). No secrets logged."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet  # noqa: E402


def _post(url: str, body: dict, headers: dict) -> tuple[bool, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return True, f"status={resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"http_{e.code}:{e.read()[:200].decode(errors='replace')}"
    except Exception as e:
        return False, str(e)[:200]


def main() -> int:
    load_dotenv_quiet()
    ep = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
    key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    dep = (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()
    ver = (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
    if not ep or not key or not dep:
        print(json.dumps({"ok": False, "error": "azure_env_incomplete"}))
        return 1

    body = {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
    results = {}
    native_url = f"{ep}/openai/deployments/{dep}/chat/completions?api-version={ver}"
    results["native_api_key"] = _post(native_url, body, {"api-key": key, "Content-Type": "application/json"})
    v1_url = f"{ep}/openai/v1/chat/completions"
    v1_body = {**body, "model": dep}
    results["v1_bearer"] = _post(v1_url, v1_body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    results["v1_api_key"] = _post(v1_url, v1_body, {"api-key": key, "Content-Type": "application/json"})

    ok = results["native_api_key"][0] or results["v1_api_key"][0] or results["v1_bearer"][0]
    print(json.dumps({"ok": ok, "results": {k: v[1] for k, v in results.items()}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
