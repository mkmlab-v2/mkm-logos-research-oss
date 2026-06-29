from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_config_v1.schema.json"
REGISTRY_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_registry_v1.schema.json"
KOSPI_CONFIG = ROOT / "data/commander/domain_configs/kospi_direction_prophecy_config_v1.json"
GP_CONFIG = ROOT / "data/commander/domain_configs/general_prophecy_core_config_v1.json"
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
GATE_SCRIPT = ROOT / "scripts/check_domain_prophecy_registry_v1.py"


def test_kospi_direction_config_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(KOSPI_CONFIG.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["domain_id"] == "kospi_direction"
    assert doc["archetype"] == "price_direction"


def test_general_prophecy_core_config_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(GP_CONFIG.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["archetype"] == "general_prophecy"


def test_registry_validates_and_has_13_domains() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(REGISTRY_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert len(doc["domains"]) == 13


def test_check_domain_prophecy_registry_exit_0() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
