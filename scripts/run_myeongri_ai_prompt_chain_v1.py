# -*- coding: utf-8 -*-
"""End-to-end helper: build prompt with refs, then validate LLM envelope response.

Flow:
1) Build prompt text + recommendation JSON via build_myeongri_ai_prompt_with_refs_v1
2) (Optional) validate a saved LLM response against myeongri_ai_interpretation_envelope_v1 schema
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Allow direct execution: py scripts/run_myeongri_ai_prompt_chain_v1.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_myeongri_ai_prompt_with_refs_v1 import main as build_prompt_main

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "myeongri_ai_interpretation_envelope_v1.schema.json"
DEFAULT_REC_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongri_external_reference_recommendation_latest.json"


def _extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if block:
        return json.loads(block.group(1))

    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        return json.loads(stripped[first : last + 1])
    raise ValueError("No JSON object detected in response text.")


def validate_envelope_text(response_text: str, schema_path: Path = SCHEMA_PATH) -> dict:
    try:
        import jsonschema  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("jsonschema package is required for validation.") from exc

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = _extract_json_object(response_text)
    jsonschema.Draft7Validator(schema).validate(payload)
    return payload


def _build_prompt_to_file(
    *,
    prompt_out: Path,
    recommendation_out: Path,
    profile: str,
    deterministic_json: Path | None,
    deterministic_json_inline: str,
    query: str,
    top_n: int,
    lang: str,
) -> None:
    argv = [
        "build_myeongri_ai_prompt_with_refs_v1.py",
        "--profile",
        profile,
        "--query",
        query,
        "--top-n",
        str(top_n),
        "--lang",
        lang,
        "--recommendation-out",
        str(recommendation_out),
    ]
    if deterministic_json:
        argv += ["--deterministic-json", str(deterministic_json)]
    else:
        argv += ["--deterministic-json-inline", deterministic_json_inline or "{}"]

    old_argv = sys.argv
    old_stdout = sys.stdout
    try:
        sys.argv = argv
        with prompt_out.open("w", encoding="utf-8") as f:
            sys.stdout = f
            rc = build_prompt_main()
        if rc != 0:
            raise RuntimeError(f"Prompt build failed with exit={rc}")
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="general")
    ap.add_argument("--query", default="")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--deterministic-json", type=Path)
    ap.add_argument("--deterministic-json-inline", default="")
    ap.add_argument("--prompt-out", type=Path, required=True)
    ap.add_argument("--recommendation-out", type=Path, default=DEFAULT_REC_OUT)
    ap.add_argument("--response-file", type=Path, help="Optional LLM response text/json file to validate")
    ap.add_argument("--validated-envelope-out", type=Path, help="Optional path to save parsed+validated envelope JSON")
    args = ap.parse_args()

    _build_prompt_to_file(
        prompt_out=args.prompt_out,
        recommendation_out=args.recommendation_out,
        profile=args.profile,
        deterministic_json=args.deterministic_json,
        deterministic_json_inline=args.deterministic_json_inline,
        query=args.query,
        top_n=args.top_n,
        lang=args.lang,
    )
    print(f"prompt_written={args.prompt_out}")
    print(f"recommendation_written={args.recommendation_out}")

    if args.response_file:
        response_text = args.response_file.read_text(encoding="utf-8")
        envelope = validate_envelope_text(response_text=response_text, schema_path=SCHEMA_PATH)
        if args.validated_envelope_out:
            args.validated_envelope_out.write_text(
                json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"validated_envelope_written={args.validated_envelope_out}")
        else:
            print("validated_envelope_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
