#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM backends for news neutralizer shadow v1 — Azure OpenAI · Gemini developer · Vertex."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

VALID_BILLING = frozenset({"auto", "azure", "developer", "vertex"})
DEFAULT_AZURE_INTER_CALL_SLEEP_SEC = 20


def azure_inter_call_sleep_sec() -> int:
    raw = (os.environ.get("MKM_AZURE_LLM_INTER_CALL_SLEEP_SEC") or "").strip()
    if not raw:
        return DEFAULT_AZURE_INTER_CALL_SLEEP_SEC
    try:
        return max(0, min(120, int(raw)))
    except ValueError:
        return DEFAULT_AZURE_INTER_CALL_SLEEP_SEC


def sleep_after_azure_call() -> None:
    delay = azure_inter_call_sleep_sec()
    if delay > 0:
        time.sleep(delay)


def load_workspace_dotenv() -> None:
    path = ROOT / ".env"
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


def azure_openai_config() -> dict[str, str] | None:
    endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    api_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    deployment = (
        (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        or (os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or "").strip()
    )
    if not endpoint or not api_key or not deployment:
        return None
    ver = (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
    timeout_ms = int((os.environ.get("AZURE_OPENAI_FETCH_TIMEOUT_MS") or "120000").strip() or "120000")
    dep = urllib.parse.quote(deployment, safe="")
    api_v = urllib.parse.quote(ver, safe="")
    url = f"{endpoint}/openai/deployments/{dep}/chat/completions?api-version={api_v}"
    return {
        "url": url,
        "api_key": api_key,
        "deployment": deployment,
        "timeout_sec": max(10, timeout_ms // 1000),
    }


def _developer_api_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY", "GOOGLE_API_KEY"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        agent = get_security_agent()
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            v = agent.get_env_var(name)
            if v and str(v).strip():
                return str(v).strip()
    except Exception:
        return None
    return None


def _vertex_project() -> str | None:
    for key in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_GENAI_PROJECT"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return None


def _vertex_location() -> str:
    return (
        (os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        or (os.environ.get("GOOGLE_GENAI_LOCATION") or "").strip()
        or "us-central1"
    )


def resolve_billing(billing: str) -> str:
    b = (billing or "auto").strip().lower()
    if b not in VALID_BILLING:
        raise ValueError(f"billing must be one of {sorted(VALID_BILLING)}")
    if b != "auto":
        return b
    priority = (os.environ.get("MKM_LLM_PRIORITY") or "azure_first").strip().lower()
    if priority in ("azure_first", "azure_only"):
        if azure_openai_config():
            return "azure"
        if priority == "azure_only":
            raise RuntimeError("MKM_LLM_PRIORITY=azure_only but AZURE_OPENAI_* is not configured")
    elif priority == "gemini_only":
        if _developer_api_key():
            return "developer"
        raise RuntimeError("MKM_LLM_PRIORITY=gemini_only but GEMINI/GOOGLE API key missing")
    if azure_openai_config():
        return "azure"
    if _developer_api_key():
        return "developer"
    if _vertex_project():
        return "vertex"
    raise RuntimeError(
        "auto billing: configure AZURE_OPENAI_* or GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT+ADC"
    )


def extract_json_object(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        raise ValueError("empty model response")
    if "```" in t:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
        if m:
            t = m.group(1).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(t, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("no JSON object in model response")


def azure_openai_json(
    *,
    system: str,
    user: str,
    deployment: str | None,
    timeout: int,
) -> tuple[dict[str, Any], str, str]:
    cfg = azure_openai_config()
    if not cfg:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT required")
    dep = (deployment or cfg["deployment"]).strip()
    if dep != cfg["deployment"]:
        endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
        ver = (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
        dep_q = urllib.parse.quote(dep, safe="")
        api_v = urllib.parse.quote(ver, safe="")
        url = f"{endpoint}/openai/deployments/{dep_q}/chat/completions?api-version={api_v}"
    else:
        url = cfg["url"]
    body = json.dumps(
        {
            "model": dep,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "api-key": cfg["api_key"]},
    )
    timeout_sec = timeout or cfg["timeout_sec"]
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as res:
                payload = json.loads(res.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429 and attempt < 3:
                import time

                time.sleep(min(2 ** attempt, 8))
                continue
            raise
    else:
        if last_err:
            raise last_err
        raise RuntimeError("azure_openai_json failed without response")
    text = str((payload.get("choices") or [{}])[0].get("message", {}).get("content") or "")
    parsed = extract_json_object(text)
    return parsed, text, dep


def gemini_developer_json(*, model: str, system: str, user: str, timeout: int) -> tuple[dict[str, Any], str]:
    from google import genai
    from google.genai import types

    key = _developer_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for developer billing")
    timeout_ms = max(10_000, int(timeout) * 1000)
    client = genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=user)])],
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    raw = (resp.text or "").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("model returned non-object JSON")
    return parsed, raw


def gemini_vertex_json(*, model: str, system: str, user: str, timeout: int) -> tuple[dict[str, Any], str]:
    from google import genai
    from google.genai import types

    proj = _vertex_project()
    if not proj:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT required for vertex billing")
    timeout_ms = max(10_000, int(timeout) * 1000)
    client = genai.Client(
        vertexai=True,
        project=proj,
        location=_vertex_location(),
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    resp = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=user)])],
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    raw = (resp.text or "").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("model returned non-object JSON")
    return parsed, raw


def llm_json(
    *,
    billing: str,
    system: str,
    user: str,
    timeout: int,
    flash_model: str,
    pro_model: str,
    azure_deployment: str | None,
    use_pro_model: bool = False,
) -> tuple[dict[str, Any], str, str, str]:
    """Returns (parsed, raw, resolved_billing, model_label)."""
    load_workspace_dotenv()
    resolved = resolve_billing(billing)
    if resolved == "azure":
        parsed, raw, dep = azure_openai_json(
            system=system,
            user=user,
            deployment=azure_deployment,
            timeout=timeout,
        )
        sleep_after_azure_call()
        return parsed, raw, resolved, dep
    model = pro_model if use_pro_model else flash_model
    if resolved == "developer":
        parsed, raw = gemini_developer_json(model=model, system=system, user=user, timeout=timeout)
        return parsed, raw, resolved, model
    if resolved == "vertex":
        parsed, raw = gemini_vertex_json(model=model, system=system, user=user, timeout=timeout)
        return parsed, raw, resolved, model
    raise RuntimeError(f"unsupported billing: {resolved}")
