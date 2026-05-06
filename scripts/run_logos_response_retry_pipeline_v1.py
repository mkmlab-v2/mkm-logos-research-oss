#!/usr/bin/env python3
"""Retry orchestrator for logos_response_v1 validation/render pipeline.

This script is intentionally model-agnostic: it consumes one or more raw
candidate files (plain JSON, fenced JSON, or noisy LLM text), then:
1) extracts JSON object
2) validates schema + banned phrases
3) renders markdown brief

It picks the first successful candidate and writes:
- normalized JSON (`--output-json`)
- markdown brief (`--output-md`)
- optional run report (`--report-json`)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.logos_response_validator_v1 import (
        DEFAULT_SCHEMA,
        parse_llm_payload,
        render_to_markdown,
        resolve_schema_path,
        validate_all,
    )
except ModuleNotFoundError:
    from logos_response_validator_v1 import (  # type: ignore
        DEFAULT_SCHEMA,
        parse_llm_payload,
        render_to_markdown,
        resolve_schema_path,
        validate_all,
    )
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_selected_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_brief_latest.md"
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_path(root: Path, p: str) -> Path:
    raw = Path(p)
    return raw if raw.is_absolute() else (root / raw)


def run_retry(
    *,
    schema_arg: str,
    candidates: list[Path],
    strict_json: bool,
    max_attempts: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    history: list[dict[str, Any]] = []
    for idx, cand in enumerate(candidates[:max_attempts], start=1):
        step: dict[str, Any] = {"attempt": idx, "path": str(cand)}
        if not cand.is_file():
            step["status"] = "missing_input"
            history.append(step)
            continue
        raw = cand.read_text(encoding="utf-8")
        try:
            doc = parse_llm_payload(raw, strict=strict_json)
        except Exception as exc:  # noqa: BLE001
            step["status"] = "extract_fail"
            step["error"] = str(exc)
            history.append(step)
            continue
        schema_path = resolve_schema_path(schema_arg, doc)
        step["schema_path"] = str(schema_path)
        schema_errs, ban_errs = validate_all(doc, schema_path)
        if schema_errs:
            step["status"] = "schema_fail"
            step["errors"] = schema_errs
            history.append(step)
            continue
        if ban_errs:
            step["status"] = "banned_fail"
            step["errors"] = ban_errs
            history.append(step)
            continue
        step["status"] = "ok"
        history.append(step)
        return doc, history
    return None, history


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--schema",
        default="",
        help="Optional schema path override. If omitted, auto-select by doc.schema.",
    )
    ap.add_argument(
        "--input",
        "-i",
        required=True,
        help="Primary raw candidate (JSON or fenced text).",
    )
    ap.add_argument(
        "--retry-input",
        action="append",
        default=[],
        help="Additional retry candidate paths (checked in order).",
    )
    ap.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Max candidate attempts to evaluate (default: 5).",
    )
    ap.add_argument(
        "--strict-json",
        action="store_true",
        help="Require each candidate to be a single JSON object only.",
    )
    ap.add_argument(
        "--output-json",
        default=str(DEFAULT_OUT_JSON),
        help="Selected normalized JSON output path.",
    )
    ap.add_argument(
        "--output-md",
        default=str(DEFAULT_OUT_MD),
        help="Rendered markdown output path.",
    )
    ap.add_argument(
        "--report-json",
        default=str(DEFAULT_REPORT),
        help="Retry report output path.",
    )
    args = ap.parse_args()

    schema_arg = str(args.schema or "")
    if schema_arg:
        schema_path = _resolve_path(ROOT, schema_arg).resolve()
        if not schema_path.is_file():
            print(f"ERROR: schema missing: {schema_path}")
            return 2

    candidate_paths = [_resolve_path(ROOT, args.input).resolve()]
    candidate_paths.extend(_resolve_path(ROOT, p).resolve() for p in args.retry_input)

    chosen, history = run_retry(
        schema_arg=schema_arg,
        candidates=candidate_paths,
        strict_json=bool(args.strict_json),
        max_attempts=max(1, int(args.max_attempts)),
    )

    report = {
        "schema": "logos_response_retry_report_v1",
        "generated_at_utc": _now(),
        "strict_json": bool(args.strict_json),
        "max_attempts": max(1, int(args.max_attempts)),
        "attempts": history,
        "selected": chosen is not None,
    }

    report_out = _resolve_path(ROOT, args.report_json).resolve()
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if chosen is None:
        print(f"WROTE: {report_out}")
        print("RESULT: no valid candidate")
        return 1

    out_json = _resolve_path(ROOT, args.output_json).resolve()
    out_md = _resolve_path(ROOT, args.output_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(chosen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_to_markdown(chosen), encoding="utf-8")

    print(f"WROTE: {out_json}")
    print(f"WROTE: {out_md}")
    print(f"WROTE: {report_out}")
    print("RESULT: selected valid candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
