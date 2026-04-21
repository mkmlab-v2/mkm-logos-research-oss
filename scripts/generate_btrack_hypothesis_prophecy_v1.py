#!/usr/bin/env python3
"""Generate B-Track hypothesis JSON (schema btrack_hypothesis_prophecy_v1) from LLM bundle.

Modes:
  --stub    Deterministic hypothesis from fusion_stub consensus (no API; CI-safe).
  --gemini  Call Gemini (requires GEMINI_API_KEY); model outputs JSON only, then validate.

Output: docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"

SCHEMA_ID = "btrack_hypothesis_prophecy_v1"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_hypothesis(doc: dict[str, Any]) -> list[str]:
    """Return list of error strings; empty if OK. Works without jsonschema package."""
    errs: list[str] = []
    if doc.get("schema") != SCHEMA_ID:
        errs.append(f"schema must be {SCHEMA_ID!r}")
    if doc.get("hypothesis_tier") != "B":
        errs.append("hypothesis_tier must be B")
    if doc.get("boundary_ack") is not True:
        errs.append("boundary_ack must be true")
    ts = doc.get("ts_utc")
    if not isinstance(ts, str) or not ts.strip():
        errs.append("ts_utc required")
    lab = doc.get("label")
    if not isinstance(lab, str) or "[HYPO]" not in lab:
        errs.append("label must include [HYPO]")
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        errs.append("prediction object required")
    else:
        inst = pred.get("instrument")
        hor = pred.get("horizon")
        dire = pred.get("direction")
        if inst not in ("kospi", "btc", "none", "multi"):
            errs.append("prediction.instrument invalid enum")
        if not isinstance(hor, str) or not hor.strip():
            errs.append("prediction.horizon required")
        if dire not in ("bull", "bear", "neutral", "abstain"):
            errs.append("prediction.direction invalid enum")
        cf = pred.get("confidence")
        if cf is not None and (not isinstance(cf, (int, float)) or not (0.0 <= float(cf) <= 1.0)):
            errs.append("prediction.confidence must be null or 0..1")
    return errs


def _try_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    try:
        schema = _load_json(schema_path)
        jsonschema.Draft202012Validator(schema).validate(doc)
    except Exception as e:  # noqa: BLE001
        return [str(e)]
    return []


def _sign_to_direction(sign: str) -> str:
    s = (sign or "").strip().lower()
    if s == "bull":
        return "bull"
    if s == "bear":
        return "bear"
    return "neutral"


def _build_stub_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    cs = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    consensus_sign = str(cs.get("consensus_sign") or "neutral").lower()
    direction = _sign_to_direction(consensus_sign)
    conf = cs.get("consensus_confidence")
    try:
        cfn = float(conf) if conf is not None else 0.45
    except (TypeError, ValueError):
        cfn = 0.45
    cfn = max(0.0, min(1.0, cfn))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ID,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": "[HYPO] Stub from fusion consensus_sign only — not live trading; sasang [NON-MEDICAL] if used.",
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
        },
        "prediction": {
            "instrument": "multi",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(cfn, 4),
        },
        "provenance": {
            "llm_model": "stub_heuristic_v1",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (default heuristic)",
        },
    }


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            o = json.loads(m.group(1).strip())
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            pass
    try:
        o = json.loads(text)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_gemini_doc(doc: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Apply conservative post-processing so gemini output does not stick to neutral."""
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        return doc
    direction = str(pred.get("direction") or "").strip().lower()
    if direction not in ("neutral", "abstain"):
        return doc

    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    c_score_raw = consensus.get("consensus_score")
    try:
        c_score = float(c_score_raw)
    except (TypeError, ValueError):
        c_score = 0.0

    fallback_dir = "neutral"
    # Favor directional call unless consensus is near-zero.
    if c_score >= 0.08:
        fallback_dir = "bull"
    elif c_score <= -0.08:
        fallback_dir = "bear"
    else:
        logos = bundle.get("artifacts", {}).get("logos_independent_lens") or {}
        logos_scores = logos.get("scores") if isinstance(logos.get("scores"), dict) else {}
        try:
            logos_ds = float(logos_scores.get("direction_score"))
        except (TypeError, ValueError):
            logos_ds = 0.0
        if logos_ds >= 0.05:
            fallback_dir = "bull"
        elif logos_ds <= -0.05:
            fallback_dir = "bear"

    if fallback_dir != "neutral":
        pred["direction"] = fallback_dir
        cf = pred.get("confidence")
        try:
            cfn = float(cf) if cf is not None else 0.0
        except (TypeError, ValueError):
            cfn = 0.0
        pred["confidence"] = round(max(cfn, 0.51), 4)
        label = str(doc.get("label") or "").strip()
        suffix = f" | neutral->{fallback_dir}_fallback"
        if suffix not in label:
            doc["label"] = f"{label}{suffix}" if label else f"[HYPO] neutral->{fallback_dir}_fallback"
    return doc


def _run_gemini(bundle_path: Path, *, model: str, timeout: int, bundle: dict[str, Any]) -> dict[str, Any]:
    key = __import__("os").getenv("GEMINI_API_KEY") or __import__("os").getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for --gemini")

    bundle_text = bundle_path.read_text(encoding="utf-8")
    schema_text = (ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json").read_text(
        encoding="utf-8"
    )
    prompt = f"""You are a B-Track hypothesis generator only. Output a single JSON object, no markdown, no commentary.

Required schema name: {SCHEMA_ID}
Required fields: schema, hypothesis_tier (must be \"B\"), boundary_ack (true), ts_utc (ISO UTC), label (must contain [HYPO]), prediction.instrument, prediction.horizon, prediction.direction, prediction.confidence (optional).

prediction.direction must be one of: bull, bear, neutral, abstain.
prediction.instrument one of: kospi, btc, none, multi.
Avoid neutral/abstain unless evidence is truly indecisive (very low directional edge).

Input bundle (read-only context):
{bundle_text[:120000]}

JSON Schema reference (follow required + enums):
{schema_text[:80000]}
"""
    from google import genai
    from google.genai import types

    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout) * 1000)
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    raw = (resp.text or "").strip()
    doc = _extract_json_blob(raw)
    if not doc:
        raise RuntimeError(f"Gemini did not return parseable JSON. Raw (truncated): {raw[:2000]!r}")
    return _normalize_gemini_doc(doc, bundle)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate btrack_hypothesis_prophecy v1 JSON.")
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--gemini",
        action="store_true",
        help="Call Gemini (needs GEMINI_API_KEY). Default: heuristic stub from bundle (no API).",
    )
    ap.add_argument("--model", type=str, default="gemini-2.5-flash")
    ap.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds for Gemini (sent as ms to google.genai; min 10s server-side).",
    )
    ap.add_argument("--validate-only", type=Path, metavar="FILE", help="Validate existing JSON; exit 1 on error.")
    args = ap.parse_args()

    if args.validate_only:
        doc = _load_json(args.validate_only)
        errs = _validate_hypothesis(doc)
        js_errs = _try_jsonschema(doc, args.schema)
        errs.extend(js_errs)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("OK:", args.validate_only)
        return 0

    if not args.bundle.is_file():
        print(f"Bundle missing: {args.bundle}", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle)

    if args.gemini:
        doc = _run_gemini(args.bundle, model=args.model, timeout=args.timeout, bundle=bundle)
    else:
        doc = _build_stub_from_bundle(bundle)

    errs = _validate_hypothesis(doc)
    js_errs = _try_jsonschema(doc, args.schema)
    errs.extend(js_errs)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
