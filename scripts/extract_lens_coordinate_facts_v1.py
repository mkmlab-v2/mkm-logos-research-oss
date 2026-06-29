#!/usr/bin/env python3
"""Extract lens coordinate facts from paper text using micro-schema (B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SCHEMA = ROOT / "docs/final/schemas/ijeoma_lens_fact_schema_v1.json"
LENS_SCHEMA_MAP = {
    "ijeoma": DEFAULT_SCHEMA,
    "logos": ROOT / "docs/final/schemas/logos_lens_fact_schema_v1.json",
    "myeongri": ROOT / "docs/final/schemas/myeongri_lens_fact_schema_v1.json",
}

ACCEPTED_SCHEMA_IDS = frozenset({"lens_fact_schema_v1", "ijeoma_lens_fact_schema_v1"})


def load_lens_schema(lens: str, schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or LENS_SCHEMA_MAP.get(lens)
    if path is None or not Path(path).is_file():
        raise FileNotFoundError(f"no lens schema for {lens}")
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema_id = doc.get("schema")
    if schema_id not in ACCEPTED_SCHEMA_IDS:
        raise ValueError(f"unsupported schema: {schema_id}")
    if doc.get("lens") and doc.get("lens") != lens:
        raise ValueError(f"schema lens mismatch: {doc.get('lens')} != {lens}")
    return doc


def _count_pattern_hits(text: str, patterns: list[str]) -> tuple[int, list[str]]:
    total = 0
    samples: list[str] = []
    for pat in patterns:
        try:
            matches = list(re.finditer(re.escape(pat), text))
        except re.error:
            matches = []
        total += len(matches)
        for m in matches[:2]:
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            if snippet and snippet not in samples:
                samples.append(snippet[:120])
    return total, samples[:3]


def extract_coordinate_facts(
    text: str,
    *,
    lens: str,
    schema_path: Path | None = None,
    title: str = "",
) -> list[dict[str, Any]]:
    schema = load_lens_schema(lens, schema_path)
    facts: list[dict[str, Any]] = []
    for field in schema.get("fields") or []:
        field_id = str(field.get("field_id") or "")
        patterns = list(field.get("patterns") or [])
        if not field_id or not patterns:
            continue
        hit_count, samples = _count_pattern_hits(text, patterns)
        if hit_count <= 0:
            continue
        sample_arm = samples[0] if samples else (title[:120] or field_id)
        facts.append(
            {
                "fact_id": f"coord_{field_id}",
                "metric_name": str(field.get("metric_name") or "coordinate_hit_count"),
                "value": float(hit_count),
                "unit": "count",
                "comparison_arm": sample_arm,
                "field_id": field_id,
                "label_ko": field.get("label_ko"),
                "pattern_samples": samples,
                "verification_status": "Unknown",
                "verification_method": "abstract_only",
            }
        )
    return facts


def coordinate_facts_to_markdown(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return ""
    lines = [
        "## Lens coordinates (schema-guided — verify against excerpt)",
        "",
        "Regex hits on full extracted text — **not** LLM invention.",
        "",
    ]
    for fact in facts:
        fid = fact["fact_id"]
        lines.extend(
            [
                f"### fact_id: {fid}",
                f"- metric_name: {fact['metric_name']}",
                f"- value: {int(fact['value']) if fact['value'] == int(fact['value']) else fact['value']}",
                f"- unit: {fact.get('unit', 'count')}",
                f"- comparison_arm: {fact['comparison_arm'][:120]}",
                f"- verification_status: {fact.get('verification_status', 'Unknown')}",
                f"- verification_method: {fact.get('verification_method', 'abstract_only')}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract lens coordinate facts from text file")
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--lens", default="ijeoma")
    ap.add_argument("--schema", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    text = args.input.read_text(encoding="utf-8", errors="replace")
    facts = extract_coordinate_facts(text, lens=args.lens, schema_path=args.schema)
    doc = {
        "schema": "lens_coordinate_extract_v1",
        "lens": args.lens,
        "source": str(args.input),
        "fact_count": len(facts),
        "facts": facts,
    }
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "fact_count": len(facts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
