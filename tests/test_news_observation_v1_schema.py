# Keywords: news_observation_v1, direction_label_bar_v1, jsonschema, B-track
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_schema(name: str) -> dict:
    p = ROOT / "docs" / "final" / "schemas" / name
    return json.loads(p.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def test_news_observation_v1_sample_jsonl_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema("news_observation_v1.schema.json")
    v = jsonschema.Draft7Validator(schema)
    fixture = ROOT / "tests" / "fixtures" / "news_observation_v1.sample.jsonl"
    rows = list(_iter_jsonl(fixture))
    assert len(rows) == 10
    for row in rows:
        v.validate(row)


def test_direction_label_bar_v1_sample_jsonl_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema("direction_label_bar_v1.schema.json")
    v = jsonschema.Draft7Validator(schema)
    fixture = ROOT / "tests" / "fixtures" / "direction_label_bar_v1.sample.jsonl"
    rows = list(_iter_jsonl(fixture))
    assert len(rows) == 5
    for row in rows:
        v.validate(row)


def test_news_observation_text_sha256_matches_canonical_utf8():
    import hashlib

    fixture = ROOT / "tests" / "fixtures" / "news_observation_v1.sample.jsonl"
    for row in _iter_jsonl(fixture):
        text = row["canonical_text"]
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert row["text_sha256"] == expected
