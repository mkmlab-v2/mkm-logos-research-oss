# -*- coding: utf-8 -*-
"""한의 의사용 CDS 보조 출력 봉투(v1) 조립: 상위 고정 필드 + 입력 페이로드 병합 후 JSON Schema 검증.

LLM/RAG 호출 없음. 배포 시 RAG 스냅샷·감사 로그와 함께 사용.

SSOT: docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "km_physician_cds_assist_envelope_v1.schema.json"

DEFAULT_DISCLAIMER_ACK = (
    "This CDS artifact assists licensed physicians only; "
    "not a standalone diagnosis or prescription."
)

# Payload keys accepted from caller (merged onto envelope skeleton). Const fields are always set by builder.
ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "clinical_question",
        "evidence_assessment",
        "evidence_gap_notes",
        "patient_context_summary",
        "evidence_items",
        "differential_framework",
        "red_flags_and_escalation",
        "suggested_next_steps_for_physician",
        "confidence",
        "rag_manifest",
        "audit",
        "disclaimer_ack",
    }
)


def _base_envelope() -> dict[str, Any]:
    return {
        "schema": "km_physician_cds_assist_envelope_v1",
        "version": "1.0.0",
        "intent": "physician_clinical_decision_support",
        "boundary_ack": True,
        "role_contract": {
            "cds_only_not_standalone_diagnosis": True,
            "physician_final_authority": True,
            "not_emergency_disposition_final": True,
        },
        "human_physician_review_required": True,
    }


def build_envelope_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge ``payload`` onto CDS envelope constants and validate against Draft-07 schema.

    Required in ``payload``: ``clinical_question``, ``evidence_assessment``.
    If ``evidence_assessment`` is ``partial`` or ``insufficient``, ``evidence_gap_notes`` is required (schema).

    Raises:
        ValueError: unknown keys, missing required fields, or pre-schema constraint violations.
        jsonschema.ValidationError: schema validation failed (if jsonschema installed).
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    unknown = set(payload) - ALLOWED_PAYLOAD_KEYS
    if unknown:
        raise ValueError(f"Unknown payload keys: {sorted(unknown)}")

    cq = payload.get("clinical_question")
    if not isinstance(cq, str) or len(cq.strip()) < 4:
        raise ValueError("clinical_question is required (string, minLength 4 per schema context)")

    ev = payload.get("evidence_assessment")
    if ev not in ("sufficient", "partial", "insufficient"):
        raise ValueError("evidence_assessment is required: sufficient | partial | insufficient")

    if ev in ("partial", "insufficient"):
        gap = payload.get("evidence_gap_notes")
        if not isinstance(gap, str) or len(gap.strip()) < 8:
            raise ValueError(
                "evidence_gap_notes is required (minLength 8) when evidence_assessment is partial or insufficient"
            )

    out = dict(_base_envelope())
    for k in ALLOWED_PAYLOAD_KEYS:
        if k in payload:
            out[k] = payload[k]

    if "disclaimer_ack" not in out or not isinstance(out.get("disclaimer_ack"), str):
        out["disclaimer_ack"] = DEFAULT_DISCLAIMER_ACK
    elif len(out["disclaimer_ack"]) < 24:
        raise ValueError("disclaimer_ack must be at least 24 characters")

    if "evidence_items" not in out:
        out["evidence_items"] = []
    elif not isinstance(out["evidence_items"], list):
        raise ValueError("evidence_items must be an array when provided")

    _validate_envelope(out)
    return out


def _validate_envelope(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("jsonschema is required for validation") from e

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _load_payload(path: Path | None, stdin_text: str | None) -> dict[str, Any]:
    if path is not None:
        raw = path.read_text(encoding="utf-8")
    elif stdin_text is not None:
        raw = stdin_text
    else:
        raw = sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Root JSON must be an object")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input-json",
        type=Path,
        metavar="PATH",
        help="JSON file with CDS payload fields (use - for stdin)",
    )
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Write envelope JSON here (default: stdout)",
    )
    ap.add_argument("--pretty", action="store_true", help="Indent JSON output")
    args = ap.parse_args()

    try:
        if args.input_json is not None:
            if str(args.input_json) == "-":
                payload = _load_payload(None, sys.stdin.read())
            else:
                payload = _load_payload(args.input_json, None)
        else:
            payload = _load_payload(None, None)

        envelope = build_envelope_from_payload(payload)
    except (ValueError, json.JSONDecodeError, OSError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # jsonschema.ValidationError and others
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    text = json.dumps(envelope, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text.rstrip() + "\n", encoding="utf-8")
    else:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
