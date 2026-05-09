#!/usr/bin/env python3
"""Check Google Gen AI connectivity without printing secrets.

Two billing surfaces:
  A) Gemini Developer API — GEMINI_API_KEY / GOOGLE_API_KEY (often “AI Studio” key).
     과금이 어떤 GCP 결제 계정·크레딧에 묶이는지는 Google 계정의 프로젝트 연동 설정에 따름.
  B) Vertex AI — GOOGLE_CLOUD_PROJECT + 리전 + ADC (서비스 계정 JSON 또는 gcloud adc).
     해당 GCP 프로젝트에 연결된 Billing / 크레딧이 적용되는 전형적인 경로.

Exit 0 if at least one path is usable; 1 if neither.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _api_key_from_env() -> str | None:
    g = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if g:
        return g
    o = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    return o or None


def _api_key_from_dpapi() -> str | None:
    try:
        sys.path.insert(0, str(_REPO_ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        agent = get_security_agent()
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            v = agent.get_env_var(name)
            if v and str(v).strip():
                return str(v).strip()
    except Exception:
        return None
    return None


def _resolve_key() -> tuple[str | None, str]:
    k = _api_key_from_env()
    if k:
        return k, "environment"
    k = _api_key_from_dpapi()
    if k:
        return k, "dpapi_store"
    return None, "none"


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


def _vertex_env_explicit() -> bool:
    return os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _creds_file_hint() -> tuple[bool, str | None]:
    p = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if not p:
        return False, None
    ok = Path(p).is_file()
    return ok, p


def cmd_check() -> int:
    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("google-genai not installed: py -m pip install google-genai", file=sys.stderr)
        return 1

    print("google_genai_import: ok")

    # Path A: Developer API key
    k, src = _resolve_key()
    print(f"developer_api_key: {'yes' if k else 'no'}")
    if k:
        print(f"developer_api_key_source: {src}")

    # Path B: Vertex (GCP billing / credits)
    proj = _vertex_project()
    loc = _vertex_location()
    creds_ok, creds_path = _creds_file_hint()
    print(f"vertex_project: {proj or '(unset)'}")
    print(f"vertex_location: {loc}")
    print(f"GOOGLE_GENAI_USE_VERTEXAI: {_vertex_env_explicit()}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS_file_exists: {creds_ok}")
    if creds_path:
        print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

    vertex_ready = bool(proj)
    dev_ready = bool(k)

    if not vertex_ready and not dev_ready:
        print(
            "\nNeither path ready:\n"
            "  Vertex: set GOOGLE_CLOUD_PROJECT (or GOOGLE_CLOUD_PROJECT_ID) and ADC "
            "(GOOGLE_APPLICATION_CREDENTIALS or gcloud auth application-default login).\n"
            "  Developer API: set GEMINI_API_KEY from AI Studio, or DPAPI store.",
            file=sys.stderr,
        )
        return 1

    if vertex_ready:
        print("\nvertex_hint: 과금·크레딧은 이 프로젝트에 연결된 Billing 계정을 따릅니다 (콘솔에서 확인).")
    if dev_ready:
        print(
            "\ndeveloper_api_hint: 키만으로는 크레딧 적용 여부를 코드에서 확정할 수 없음 — "
            "AI Studio↔GCP 결제 연동 설정을 콘솔에서 확인."
        )

    return 0


def cmd_smoke(model: str, prompt: str) -> int:
    k, src = _resolve_key()
    if not k:
        print("No API key (env or DPAPI). Use smoke-vertex for Vertex.", file=sys.stderr)
        return 1
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("pip install google-genai", file=sys.stderr)
        return 1

    client = genai.Client(api_key=k)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=256,
            temperature=0.2,
        ),
    )
    text = (resp.text or "").strip()
    print(f"billing_surface: gemini_developer_api")
    print(f"model: {model}")
    print(f"key_source: {src}")
    print("response_preview:", text[:500] + ("…" if len(text) > 500 else ""))
    return 0


def cmd_smoke_vertex(model: str, prompt: str) -> int:
    proj = _vertex_project()
    if not proj:
        print("Set GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_PROJECT_ID.", file=sys.stderr)
        return 1
    loc = _vertex_location()
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("pip install google-genai", file=sys.stderr)
        return 1

    client = genai.Client(vertexai=True, project=proj, location=loc)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=256,
            temperature=0.2,
        ),
    )
    text = (resp.text or "").strip()
    print(f"billing_surface: vertex_ai")
    print(f"project: {proj}")
    print(f"location: {loc}")
    print(f"model: {model}")
    print("response_preview:", text[:500] + ("…" if len(text) > 500 else ""))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Google Gen AI readiness / smoke")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Developer API key + Vertex env (no network)")

    sp = sub.add_parser("smoke", help="One call via Developer API key (uses quota)")
    sp.add_argument("--model", default="gemini-2.0-flash")
    sp.add_argument("--prompt", default="Reply with exactly: OK")

    sv = sub.add_parser(
        "smoke-vertex",
        help="One call via Vertex AI (GCP project billing / credits)",
    )
    sv.add_argument("--model", default="gemini-2.0-flash-001")
    sv.add_argument("--prompt", default="Reply with exactly: OK")

    args = p.parse_args()
    if args.cmd == "check":
        return cmd_check()
    if args.cmd == "smoke":
        return cmd_smoke(args.model, args.prompt)
    if args.cmd == "smoke-vertex":
        return cmd_smoke_vertex(args.model, args.prompt)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
