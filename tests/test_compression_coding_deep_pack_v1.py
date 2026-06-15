"""Coding deep pack PoC: zone_f_code template catalog + twin gate (B-track)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
MANIFEST = ROOT / "codebook/templates/zone_f_code_templates_manifest_v1.json"
GATE = ROOT / "docs/final/artifacts/compression_coding_deep_pack_gate_v1_latest.json"
BUILDER = ROOT / "scripts/build_compression_coding_deep_pack_gate_v1.py"

CATALOG_SHA256_PIN = "68192997a2e18318f362419a62ddf43a5ec14164302ae4008bbd19449641898a"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_zone_f_code_templates_manifest_matches_jsonl() -> None:
    assert TEMPLATES.is_file()
    assert MANIFEST.is_file()
    manifest = _load(MANIFEST)
    assert manifest["schema"] == "zone_f_code_templates_manifest_v1"
    assert manifest["row_count"] == 8
    assert manifest["catalog_sha256"] == CATALOG_SHA256_PIN
    h = hashlib.sha256(TEMPLATES.read_bytes()).hexdigest()
    assert h == CATALOG_SHA256_PIN


def test_coding_deep_pack_gate_schema_and_twin_axes() -> None:
    assert GATE.is_file()
    assert BUILDER.is_file()
    gate = _load(GATE)
    assert gate["schema"] == "compression_coding_deep_pack_gate_v1"
    assert gate["track_a_active_untouched"] is True
    assert gate["send_gate"] == "HOLD"
    assert gate["twin_metrics_axis"]["primary_pair"] == ["saving_rate", "exact_restore_ok"]
    assert gate["twin_metrics_axis"]["secondary_axis"] == "jaccard_proxy"
    assert "Tier A operational pass rate" in gate["tier_a_status_note"]
    assert gate["template_catalog"]["catalog_sha256"] == CATALOG_SHA256_PIN
    assert len(gate["cases"]) == 8
    for case in gate["cases"]:
        assert case.get("roundtrip_path") == "template_catalog_wire_v1"
        assert "saving_rate" in case
        assert "exact_restore_ok" in case
        assert "jaccard_proxy" in case
    assert gate["summary"]["exact_restore_pass_count"] == 8
    assert float(gate["summary"]["mean_saving_rate"]) > 0.0


def test_coding_deep_pack_wire_codec_exact_restore() -> None:
    from scripts.compression_coding_deep_pack_v1_lib import (
        expand_template_wire,
        load_default_catalog,
        measure_template_wire_twin,
        wire_to_compact,
        build_wire_packet,
    )

    rows, catalog_sha256 = load_default_catalog()
    row = rows[0]
    wire = build_wire_packet(template_id=str(row["template_id"]), catalog_sha256=catalog_sha256)
    compact = wire_to_compact(wire)
    restored = expand_template_wire(compact, rows, expected_catalog_sha256=catalog_sha256)
    assert restored == row["snippet"]
    twin = measure_template_wire_twin(
        original_snippet=str(row["snippet"]),
        template_id=str(row["template_id"]),
        catalog_sha256=catalog_sha256,
        catalog_rows=rows,
    )
    assert twin["exact_restore_ok"] is True
    assert twin["jaccard_proxy"] == 1.0


def test_manifest_idempotent_when_catalog_unchanged() -> None:
    from scripts.build_compression_coding_deep_pack_gate_v1 import build_manifest

    before = _load(MANIFEST)["generated_at_utc"]
    rebuilt = build_manifest(TEMPLATES, MANIFEST)
    after = rebuilt["generated_at_utc"]
    assert after == before


def test_coding_deep_pack_gate_regenerate_smoke() -> None:
    pytest.importorskip("fastapi")
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
