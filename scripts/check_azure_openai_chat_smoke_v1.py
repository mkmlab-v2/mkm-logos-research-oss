#!/usr/bin/env python3
"""Smoke-test Azure OpenAI chat/completions from workspace .env (no secrets printed)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _cfg() -> dict | None:
    endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    api_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    deployment = (
        os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        or ""
    ).strip()
    if not endpoint or not api_key or not deployment:
        return None
    ver = (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
    dep = urllib.parse.quote(deployment, safe="")
    api_v = urllib.parse.quote(ver, safe="")
    url = f"{endpoint}/openai/deployments/{dep}/chat/completions?api-version={api_v}"
    return {"url": url, "api_key": api_key, "deployment": deployment}


def main() -> int:
    import urllib.parse  # noqa: PLC0415

    _load_dotenv(ROOT / ".env")
    cfg = _cfg()
    out: dict = {"schema": "azure_openai_chat_smoke_v1", "ok": False}
    if not cfg:
        out["error"] = "missing_env"
        out["required"] = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    body = json.dumps(
        {
            "model": cfg["deployment"],
            "messages": [{"role": "user", "content": "Reply with exactly: azure_ok"}],
            "max_tokens": 16,
            "temperature": 0,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        cfg["url"],
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "api-key": cfg["api_key"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
        text = (payload.get("choices") or [{}])[0].get("message", {}).get("content", "")
        out["ok"] = bool(str(text).strip())
        out["deployment"] = cfg["deployment"]
        out["status"] = res.status
        out["reply_preview"] = str(text).strip()[:120]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    except urllib.error.HTTPError as e:
        out["error"] = f"http_{e.code}"
        out["body_preview"] = e.read().decode("utf-8", errors="replace")[:300]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1
    except Exception as e:
        out["error"] = type(e).__name__
        out["message"] = str(e)[:200]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
