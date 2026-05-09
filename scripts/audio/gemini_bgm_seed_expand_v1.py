#!/usr/bin/env python3
"""
Expand MKM audio seed JSON via Gemini (Developer API or Vertex AI).

Billing surfaces (same as scripts/check_google_genai_readiness_v1.py):
  - developer: GEMINI_API_KEY / GOOGLE_API_KEY (AI Studio–style key)
  - vertex: GOOGLE_CLOUD_PROJECT + ADC → GCP billing / credits

Default billing (no env): ``developer`` — ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY`` from AI Studio (free tier within Google quotas).
For org GCP/Vertex credits set ``MKM_AUDIO_GEMINI_BILLING=auto`` or ``vertex`` (see ``--billing``).
``auto`` picks Vertex when ``GOOGLE_CLOUD_PROJECT`` is set and ADC works; else Developer API key.

Output is structured JSON for downstream generators (not raw WAV — Gemini text models).

Dependencies: pip install google-genai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _api_key_from_env() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY", "GOOGLE_API_KEY"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    return None


def _api_key_from_dpapi() -> str | None:
    try:
        sys.path.insert(0, str(_REPO_ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        agent = get_security_agent()
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            val = agent.get_env_var(name)
            if val and str(val).strip():
                return str(val).strip()
    except Exception:
        return None
    return None


def _resolve_developer_key() -> tuple[str | None, str]:
    k = _api_key_from_env()
    if k:
        return k, "environment"
    k = _api_key_from_dpapi()
    if k:
        return k, "dpapi_store"
    return None, "none"


def _billing_surface_auto() -> str:
    if _vertex_project():
        return "vertex"
    k, _ = _resolve_developer_key()
    if k:
        return "developer"
    return ""


def _make_genai_client(*, billing: str, timeout_sec: int):
    from google import genai
    from google.genai import types

    timeout_ms = max(10_000, int(timeout_sec) * 1000)
    http = types.HttpOptions(timeout=timeout_ms)

    if billing == "vertex":
        proj = _vertex_project()
        if not proj:
            raise RuntimeError("vertex billing requires GOOGLE_CLOUD_PROJECT (or GOOGLE_CLOUD_PROJECT_ID).")
        client = genai.Client(
            vertexai=True,
            project=proj,
            location=_vertex_location(),
            http_options=http,
        )
        return client, "vertex_ai"

    k, src = _resolve_developer_key()
    if not k:
        raise RuntimeError(
            "developer billing requires GEMINI_API_KEY or GOOGLE_API_KEY (or DPAPI store)."
        )
    client = genai.Client(api_key=k, vertexai=False, http_options=http)
    return client, f"gemini_developer_api:{src}"


def _system_instruction() -> str:
    return (
        "You are an assistant for BGM / underscore audio production. "
        "Given a JSON seed (mood, BPM hints, lens metadata), respond with ONE JSON object only, "
        "no markdown fences, no commentary. Schema keys:\n"
        '  "schema": "gemini_bgm_seed_expand_v1",\n'
        '  "expanded_prompt_en": string,\n'
        '  "expanded_prompt_ko": string,\n'
        '  "negative_constraints": array of strings,\n'
        '  "suggested_bpm_range": [min, max] integers,\n'
        '  "suggested_duration_sec": number,\n'
        '  "notes_for_human": string,\n'
        '  "copyright_caution": string (short reminder about training data / similarity).\n'
        "Keep prompts usable for a separate audio generator; do not claim legal clearance."
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse first JSON object from model text (handles fences, prose prefixes, nested {})."""
    t = (text or "").strip()
    if not t:
        raise ValueError("Empty model response.")
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
    raise ValueError("No JSON object found in model response.")


def run_expand(
    *,
    seed: dict[str, Any],
    billing: str,
    model: str,
    timeout_sec: int,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "schema": "gemini_bgm_seed_expand_v1",
            "billing_surface": "dry_run",
            "model": model,
            "generated_at_utc": _utc_now_iso(),
            "expanded_prompt_en": "(dry-run)",
            "expanded_prompt_ko": "(드라이런)",
            "negative_constraints": [],
            "suggested_bpm_range": [80, 120],
            "suggested_duration_sec": 32,
            "notes_for_human": "dry_run=true — no API call",
            "copyright_caution": "Verify licenses for any commercial deployment.",
            "seed_echo": seed,
        }

    from google.genai import types

    surf_auto = billing
    if surf_auto == "auto":
        surf_auto = _billing_surface_auto()
        if not surf_auto:
            raise RuntimeError(
                "auto billing: set Vertex (GOOGLE_CLOUD_PROJECT + ADC) OR Developer API key."
            )

    client, billing_tag = _make_genai_client(billing=surf_auto, timeout_sec=timeout_sec)
    user_payload = json.dumps(seed, ensure_ascii=False, indent=2)
    prompt = f"Seed JSON:\n{user_payload}\n\nRespond with the required JSON object only."

    resp = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=_system_instruction(),
            temperature=0.3,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    raw = (resp.text or "").strip()
    try:
        parsed = _extract_json_object(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"model_output_parse_failed: {e}") from e
    out = {
        **parsed,
        "billing_surface": "vertex_ai"
        if billing_tag == "vertex_ai"
        else "gemini_developer_api",
        "billing_detail": billing_tag,
        "model": model,
        "generated_at_utc": _utc_now_iso(),
        "seed_echo": seed,
    }
    return out


def _default_billing_arg() -> str:
    v = (os.environ.get("MKM_AUDIO_GEMINI_BILLING") or "").strip().lower()
    return v if v in ("auto", "developer", "vertex") else "developer"


def main() -> int:
    p = argparse.ArgumentParser(description="Gemini/Vertex BGM seed expansion (JSON meta).")
    p.add_argument("--seed-json", type=Path, required=True)
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("reports/audio/gemini_bgm_seed_expand_latest.json"),
    )
    p.add_argument(
        "--billing",
        choices=("auto", "developer", "vertex"),
        default=_default_billing_arg(),
        help=(
            "developer (default): AI Studio API key. auto: Vertex when GOOGLE_CLOUD_PROJECT + ADC else key. "
            "vertex: force Vertex. Env MKM_AUDIO_GEMINI_BILLING overrides default when set to auto|developer|vertex."
        ),
    )
    p.add_argument(
        "--model",
        default=os.environ.get("MKM_AUDIO_GEMINI_MODEL", "gemini-2.5-flash"),
        help="Override with env MKM_AUDIO_GEMINI_MODEL.",
    )
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--dry-run", action="store_true", help="Write template JSON without calling Gemini.")
    args = p.parse_args()

    if not args.dry_run:
        sys.path.insert(0, str(_REPO_ROOT / "scripts"))
        from google_paid_guard_v1 import exit_if_google_paid_blocked  # noqa: E402

        exit_if_google_paid_blocked(context="gemini_bgm_seed_expand_v1")

    seed_path = args.seed_json
    if not seed_path.is_file():
        print(f"seed-json not found: {seed_path}", file=sys.stderr)
        return 2

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    try:
        out = run_expand(
            seed=seed,
            billing=args.billing,
            model=args.model,
            timeout_sec=args.timeout,
            dry_run=args.dry_run,
        )
    except RuntimeError as e:
        msg = str(e)
        print(msg, file=sys.stderr)
        if "model_output_parse_failed" in msg:
            return 5
        return 3
    except Exception as e:
        print(f"expand_failed: {e}", file=sys.stderr)
        return 5

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(args.out_json), "billing": out.get("billing_surface")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
