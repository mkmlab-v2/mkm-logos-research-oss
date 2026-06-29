from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_public_event_lens_audio_thin_slice_example_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "docs/final/schemas/public_event_lens_audio_thin_slice_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    example_path = (
        ROOT
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/examples/public_event_lens_audio_thin_slice_v1.example.json"
    )
    doc = json.loads(example_path.read_text(encoding="utf-8"))
    block = doc["lens_audio_observability_v1"]
    jsonschema.validate(instance=block, schema=schema)


def test_jemaai_lens_audio_playback_lut_example_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "docs/final/schemas/jemaai_lens_audio_playback_lut_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    example_path = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1.example.json"
    doc = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_playback_id_in_lut_matches_ingest_example():
    lut = json.loads(
        (ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1.example.json").read_text(
            encoding="utf-8"
        )
    )
    ingest = json.loads(
        (
            ROOT
            / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/examples/public_event_lens_audio_thin_slice_v1.example.json"
        ).read_text(encoding="utf-8")
    )
    playback_id = ingest["lens_audio_observability_v1"]["playback_id"]
    assert playback_id in lut["entries"]
