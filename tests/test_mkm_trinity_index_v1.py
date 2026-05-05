from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "final" / "MKM_TRINITY_INDEX_V1.json"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_trinity_index_v1.schema.json"


@pytest.mark.parametrize("path", [INDEX, SCHEMA])
def test_mkm_trinity_index_files_exist(path: Path) -> None:
    assert path.is_file(), f"missing: {path.relative_to(ROOT)}"


def test_mkm_trinity_index_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
