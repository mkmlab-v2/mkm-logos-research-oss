"""CONSTITUTION path sidecar builder — anchor + must_keep contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_sidecar_constitution_lib_v1 import (  # noqa: E402
    CONSTITUTION_REL,
    SEGMENT_SPECS,
    build_sidecar_document,
    sha256_file,
)


def test_build_sidecar_three_segments_and_must_keep():
    doc = build_sidecar_document(ROOT)
    assert doc["schema"] == "mkm_sidecar_constitution_paths_v1"
    assert doc["research_only"] is True
    assert doc["source_ssot"] == CONSTITUTION_REL
    assert len(doc["segments"]) == len(SEGMENT_SPECS)

    for spec in SEGMENT_SPECS:
        seg = doc["segments"][spec.segment_id]
        for tag in spec.must_keep_tags:
            assert tag in seg["body_markdown"]
        assert seg["extracted_paths"]
        assert seg["line_range"][0] >= 1


def test_skip_if_unchanged_roundtrip(tmp_path: Path):
    source = ROOT / CONSTITUTION_REL
    assert source.is_file()

    doc = build_sidecar_document(ROOT)
    out = tmp_path / "sidecar.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    assert doc["source_sha256"] == sha256_file(source)
    reloaded = json.loads(out.read_text(encoding="utf-8"))
    assert reloaded["source_sha256"] == doc["source_sha256"]
