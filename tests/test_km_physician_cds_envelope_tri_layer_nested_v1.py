# Purpose: Regression — tri-layer fixture nested under CDS envelope validates after schema alignment.
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

SCHEMA = ROOT / "docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json"
FIXTURE = ROOT / "tests/fixtures/km_physician_cds_assist_envelope_with_tri_layer_v1.example.json"


def _resolver_for_envelope_schema(envelope_schema: dict) -> "jsonschema.RefResolver":
    schema_dir = SCHEMA.parent
    tri_path = schema_dir / "mkm_bianzheng_tri_layer_v1.schema.json"
    tri_schema = json.loads(tri_path.read_text(encoding="utf-8"))
    base = f"{schema_dir.as_uri()}/"
    resolver = jsonschema.RefResolver(base_uri=base, referrer=envelope_schema)
    resolver.store[envelope_schema.get("$id", "")] = envelope_schema
    resolver.store[tri_schema.get("$id", "")] = tri_schema
    resolver.store["mkm_bianzheng_tri_layer_v1.schema.json"] = tri_schema
    return resolver


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_tri_layer_nested_envelope_fixture_validates() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    resolver = _resolver_for_envelope_schema(schema)
    jsonschema.Draft7Validator(schema, resolver=resolver).validate(doc)
    assert doc.get("mkm_bianzheng_tri_layer", {}).get("schema") == "mkm_bianzheng_tri_layer_v1"
