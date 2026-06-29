#!/usr/bin/env python3
"""Build herbs_formulas_extract_v1 JSON from structured lecture markdown (B-track only).

Track B · research_only · send_gate HOLD · expert_review_required · not prescription output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
SCHEMA_PATH = ROOT / "docs/final/schemas/herbs_formulas_extract_v1.schema.json"
DEFAULT_BOUNDARY_ACK = (
    "Draft structured extract only; physician must verify before clinical use."
)

SECTION_ALIASES: dict[str, str] = {
    "clinical": "clinical",
    "research": "research",
    "education": "education",
    "임상": "clinical",
    "연구": "research",
    "교육": "education",
}

CLINICAL_STRING_FIELDS = (
    "primary_pathology",
    "formula_composition_and_roles",
    "modification_principles",
)
CLINICAL_LIST_FIELDS = (
    "representative_symptoms",
    "differential_diagnosis",
    "safety_precautions",
    "tongue_pulse_signals",
)

RESEARCH_STRING_FIELDS = (
    "research_objective",
    "study_population",
    "methodology_design",
    "primary_outcomes",
    "limitations_and_interpretation_caution",
)
RESEARCH_LIST_FIELDS = ("follow_up_questions",)

EDUCATION_LIST_FIELDS = (
    "learning_objectives",
    "core_concepts",
    "comparison_points",
    "discussion_questions",
    "quiz_items",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line.strip())
        if heading:
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            raw = heading.group(1).strip().lower()
            current_key = SECTION_ALIASES.get(raw, raw)
            current_lines = []
            continue
        if current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def _parse_list_value(raw: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[;|]", raw) if p.strip()]
    return parts


def parse_section_block(
    block: str,
    *,
    string_fields: tuple[str, ...],
    list_fields: tuple[str, ...],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    lines = block.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([a-z_]+)\s*:\s*(.*)$", line, re.IGNORECASE)
        if not match:
            continue
        key = match.group(1).lower()
        inline = match.group(2).strip()
        if key in string_fields:
            if inline:
                out[key] = inline
            continue
        if key in list_fields:
            items: list[str] = []
            if inline:
                items.extend(_parse_list_value(inline))
            while idx < len(lines):
                next_line = lines[idx].strip()
                if not next_line:
                    idx += 1
                    continue
                bullet = re.match(r"^[-*]\s+(.+)$", next_line)
                if bullet:
                    items.append(bullet.group(1).strip())
                    idx += 1
                    continue
                if re.match(r"^[a-z_]+\s*:", next_line, re.IGNORECASE):
                    break
                idx += 1
            out[key] = items
    return out


def parse_source_material_id(text: str, source_path: Path) -> str:
    match = re.search(r"\*\*source_material_id:\*\*\s*(\S+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return f"file:{source_path.stem}"


def infer_output_lane(sections_present: set[str]) -> str:
    if sections_present >= {"clinical", "research", "education"}:
        return "multi"
    if len(sections_present) == 1:
        return next(iter(sections_present))
    return "multi"


def build_herbs_formulas_extract(
    *,
    source_path: Path,
    boundary_ack: str = DEFAULT_BOUNDARY_ACK,
    output_lane: str | None = None,
    extraction_notes: str | None = None,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    sections = split_sections(text)
    clinical = parse_section_block(
        sections.get("clinical", ""),
        string_fields=CLINICAL_STRING_FIELDS,
        list_fields=CLINICAL_LIST_FIELDS,
    )
    research = parse_section_block(
        sections.get("research", ""),
        string_fields=RESEARCH_STRING_FIELDS,
        list_fields=RESEARCH_LIST_FIELDS,
    )
    education = parse_section_block(
        sections.get("education", ""),
        string_fields=(),
        list_fields=EDUCATION_LIST_FIELDS,
    )

    present = {name for name, body in sections.items() if body.strip()}
    lane = output_lane or infer_output_lane(present)
    source_id = parse_source_material_id(text, source_path)

    return {
        "schema": "herbs_formulas_extract_v1",
        "version": "1.0.0",
        "domain_lane": "herbs_formulas",
        "output_lane": lane,
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "send_gate": "HOLD",
        "expert_review_required": True,
        "boundary_ack": boundary_ack,
        "payload": {
            "clinical": clinical,
            "research": research,
            "education": education,
        },
        "provenance": {
            "source_material_ids": [source_id],
            "uncertainty_flags": ["regex_extract_not_llm_verified"],
            "extraction_notes": extraction_notes
            or f"Built from {_posix_path(source_path)} at {_utc_now()} (regex section parser).",
        },
    }


def validate_extract(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("jsonschema required for --strict") from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def default_out_path(source: Path, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    return out_dir / f"{source.stem}_herbs_formulas_extract_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build herbs_formulas_extract_v1 from lecture markdown")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--output-lane", choices=["clinical", "research", "education", "multi"], default=None)
    parser.add_argument("--boundary-ack", default=DEFAULT_BOUNDARY_ACK)
    parser.add_argument("--strict", action="store_true", help="Validate against JSON Schema (exit 2 on fail)")
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {source}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    doc = build_herbs_formulas_extract(
        source_path=source,
        boundary_ack=str(args.boundary_ack),
        output_lane=args.output_lane,
    )
    if args.strict:
        try:
            validate_extract(doc)
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": str(exc), "step": "schema_validate"}, ensure_ascii=False),
                file=sys.stderr,
            )
            return 2

    out_path = args.out.resolve() if args.out else default_out_path(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix_path(out_path),
                "source_sha256": file_sha256(source),
                "output_lane": doc["output_lane"],
                "schema_validated": bool(args.strict),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
