#!/usr/bin/env python3
"""Minimal multi-turn chat smoke test for Gemini.

Default: Developer API (GEMINI_API_KEY / GOOGLE_API_KEY / DPAPI).

Vertex (GCP project Billing / credits): pass --vertex and set GOOGLE_CLOUD_PROJECT
(+ GOOGLE_CLOUD_LOCATION, ADC via GOOGLE_APPLICATION_CREDENTIALS or gcloud adc).

Usage:
  py scripts/run_gemini_chat_smoke_v1.py --model gemini-2.0-flash
  py scripts/run_gemini_chat_smoke_v1.py --vertex --model gemini-2.0-flash-001
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _vertex_project() -> str | None:
    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_GENAI_PROJECT",
    ):
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


def _api_key() -> str | None:
    g = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if g:
        return g
    o = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    if o:
        return o
    try:
        sys.path.insert(0, str(_REPO_ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        agent = get_security_agent()
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            v = agent.get_env_var(name)
            if v and str(v).strip():
                return str(v).strip()
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vertex", action="store_true", help="Use Vertex AI (GCP billing/credits)")
    ap.add_argument(
        "--model",
        default=None,
        help="Default: gemini-2.0-flash (dev) or gemini-2.0-flash-001 (vertex)",
    )
    ap.add_argument("--user", default="Say hello in one short sentence.")
    args = ap.parse_args()

    model = args.model
    if model is None:
        model = "gemini-2.0-flash-001" if args.vertex else "gemini-2.0-flash"

    try:
        from google import genai
    except ImportError:
        print("pip install google-genai", file=sys.stderr)
        return 1

    if args.vertex:
        proj = _vertex_project()
        if not proj:
            print(
                "Vertex: set GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_PROJECT_ID.",
                file=sys.stderr,
            )
            return 1
        loc = _vertex_location()
        client = genai.Client(vertexai=True, project=proj, location=loc)
    else:
        key = _api_key()
        if not key:
            print(
                "Set GEMINI_API_KEY or GOOGLE_API_KEY (or DPAPI store), or use --vertex.",
                file=sys.stderr,
            )
            return 1
        client = genai.Client(api_key=key)

    if args.vertex:
        from google.genai import types

        r = client.models.generate_content(
            model=model,
            contents=args.user,
            config=types.GenerateContentConfig(
                max_output_tokens=256,
                temperature=0.2,
            ),
        )
        print((r.text or "").strip())
        return 0

    chat = client.chats.create(model=model)
    r = chat.send_message(args.user)
    print((r.text or "").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
