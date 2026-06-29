#!/usr/bin/env python3
"""Gate general_prophecy registries for B-track predictability harness (binary + falsifiable).

Rejects open narrative rows (non-binary outcome, weak criteria, optional vague question heuristics).
Does not score Brier; use run_btrack_predictability_harness_v1.py for the full chain.
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
SCHEMA_PATH = ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
RESULT_SCHEMA = "general_prophecy_predictability_input_gate_v1"

# Very short directional market phrases without embedded falsifiable rubric in question_text.
_VAGUE_MARKET_RE = re.compile(
    r"^(?:반도체|주가|코스피|btc|bitcoin|엔비디아|nvidia).{0,40}(?:상승|하락|오를|내릴).{0,20}\??$",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _validate_jsonschema(registry: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return []
    if not SCHEMA_PATH.is_file():
        return [f"schema_missing:{SCHEMA_PATH}"]
    schema_doc = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema_doc)
    errors = sorted(validator.iter_errors(registry), key=lambda e: list(e.path))
    return [f"jsonschema:{e.message}" for e in errors[:20]]


def validate_registry(registry: dict[str, Any], *, check_jsonschema: bool = True) -> dict[str, Any]:
    """Return gate document with accepted/rejected question lists."""
    rejections: list[dict[str, Any]] = []
    accepted: list[str] = []
    schema_errors = _validate_jsonschema(registry) if check_jsonschema else []
    if schema_errors:
        return {
            "schema": RESULT_SCHEMA,
            "generated_at_utc": _utc_now(),
            "gate_pass": False,
            "registry_schema_errors": schema_errors,
            "accepted_question_ids": [],
            "rejected": [],
            "note": "registry-level jsonschema failed",
        }

    rail = str(registry.get("research_rail") or "")
    if rail not in ("B", "OBSERVATION_ONLY"):
        rejections.append(
            {
                "question_id": "__registry__",
                "reason": "research_rail_not_b_track",
                "detail": rail,
            }
        )

    questions = registry.get("questions")
    if not isinstance(questions, list):
        rejections.append({"question_id": "__registry__", "reason": "questions_not_array"})
        questions = []

    for q in questions:
        if not isinstance(q, dict):
            rejections.append({"question_id": "__unknown__", "reason": "question_not_object"})
            continue
        qid = str(q.get("question_id") or "__missing_id__")
        reasons: list[str] = []

        outcome = q.get("outcome_spec") if isinstance(q.get("outcome_spec"), dict) else {}
        kind = str(outcome.get("kind") or "")
        if kind != "binary":
            reasons.append(f"outcome_not_binary:{kind or 'missing'}")

        criteria = str(q.get("resolution_criteria") or "")
        if len(criteria) < 40:
            reasons.append("resolution_criteria_too_short")

        deadline = str(q.get("resolution_deadline_utc") or "")
        if not _parse_utc(deadline):
            reasons.append("resolution_deadline_utc_invalid")

        qtext = str(q.get("question_text") or "")
        if len(qtext) < 20:
            reasons.append("question_text_too_short")
        elif _VAGUE_MARKET_RE.match(qtext.strip()) and len(criteria) < 80:
            reasons.append("open_narrative_market_phrase_without_rubric")

        q_rail = str(q.get("research_rail") or rail)
        if q_rail not in ("B", "OBSERVATION_ONLY"):
            reasons.append(f"question_research_rail:{q_rail}")

        if reasons:
            rejections.append({"question_id": qid, "reason": "predictability_gate", "detail": reasons})
        else:
            accepted.append(qid)

    gate_pass = len(rejections) == 0 and len(accepted) > 0
    return {
        "schema": RESULT_SCHEMA,
        "generated_at_utc": _utc_now(),
        "gate_pass": gate_pass,
        "accepted_question_ids": accepted,
        "rejected": rejections,
        "counts": {
            "accepted": len(accepted),
            "rejected": len(rejections),
        },
        "note": "binary+deadline+criteria only; Logos/GraphRAG not in scope",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, required=True)
    ap.add_argument("--output", "-o", type=Path, default=None)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--no-jsonschema", action="store_true")
    args = ap.parse_args()
    registry = _load(args.input)
    doc = validate_registry(registry, check_jsonschema=not args.no_jsonschema)
    doc["inputs"] = {"registry_path": str(args.input.resolve())}
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        sys.stdout.write(text)
        return 0 if doc.get("gate_pass") else 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(str(args.output.resolve()))
    else:
        sys.stdout.write(text)
    return 0 if doc.get("gate_pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
