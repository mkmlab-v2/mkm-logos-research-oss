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
        assert "saving_rate" in case
        assert "exact_restore_ok" in case
        assert "jaccard_proxy" in case


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
