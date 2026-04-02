"""Generate B-track hypothesis inventory schema and artifact."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://workspace.local/schemas/B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json",
    "title": "B-Track Hypothesis Inventory (document)",
    "description": "Machine-readable B-track hypotheses; see CONSTITUTION §4.5.1.",
    "type": "object",
    "required": ["schema", "disclaimer", "constitution_ref", "entries"],
    "additionalProperties": False,
    "properties": {
        "schema": {"type": "string", "const": "b_track_hypothesis_inventory_v1"},
        "disclaimer": {"type": "string", "minLength": 1},
        "generated_at_utc": {"type": "string", "format": "date-time"},
        "constitution_ref": {"type": "string"},
        "inventory_schema_path": {"type": "string"},
        "entries": {"type": "array", "items": {"$ref": "#/definitions/hypothesis_entry"}},
    },
    "definitions": {
        "hypothesis_entry": {
            "type": "object",
            "required": [
                "hypothesis_id", "hypothesis_tier", "boundary_ack", "pillar",
                "ontology_layer", "lens_family", "title",
                "falsification_condition", "promotion_status",
            ],
            "additionalProperties": True,
            "properties": {
                "hypothesis_id": {"type": "string", "pattern": r"^[A-Za-z0-9_.-]+$"},
                "created_utc": {"type": "string", "format": "date-time"},
                "hypothesis_tier": {"type": "string", "enum": ["B"]},
                "boundary_ack": {"type": "boolean", "const": True},
                "pillar": {"type": "string", "enum": ["gematria_root", "state_resonance", "semantic_trigger", "structural_fractal"]},
                "ontology_layer": {"type": "string", "enum": ["source_program", "human_lens_east", "human_lens_west", "unspecified"]},
                "lens_family": {"type": "string", "enum": ["none", "myeongni", "sasang", "ijeoma", "mixed"]},
                "equivalence_claim": {"type": "boolean"},
                "title": {"type": "string", "minLength": 1},
                "summary": {"type": "string"},
                "falsification_condition": {"type": "string", "minLength": 1},
                "promotion_status": {"type": "string", "enum": ["draft", "bench_only", "superseded", "retired"]},
                "target_state_id": {"type": "integer", "minimum": 1, "maximum": 16},
                "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "cross_links": {"type": "array"},
                "gematria_provenance": {"type": "object", "additionalProperties": True},
                "fractal_analogy": {"type": "object", "additionalProperties": True},
                "note": {"type": "string"},
            },
        },
    },
}
def main():
    p = ROOT / "docs/final/B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(SCHEMA, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    inv = ROOT / "docs/final/artifacts/B_TRACK_HYPOTHESIS_INVENTORY_V1.json"
    inv.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "b_track_hypothesis_inventory_v1",
        "disclaimer": "B-Track hypothesis inventory only; not A-track SSOT; trading engine must not load by default. Rows are [HYPO] unless promoted via §8; cross_links are thematic joins, not ontological identity.",
        "generated_at_utc": "2026-04-02T00:00:00+00:00",
        "constitution_ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §4.5.1",
        "inventory_schema_path": "docs/final/B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json",
        "entries": [],
    }
    inv.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ok", p, inv)
if __name__ == "__main__":
    main()
