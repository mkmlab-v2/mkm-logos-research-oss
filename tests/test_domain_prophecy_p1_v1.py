from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_config_v1.schema.json"
MACRO_CONFIG = ROOT / "data/commander/domain_configs/general_prophecy_macro_ai_config_v1.json"
GEO_CONFIG = ROOT / "data/commander/domain_configs/general_prophecy_geopolitics_config_v1.json"
MACRO_PACK = ROOT / "data/commander/domain_packs/general_prophecy_macro_ai_pack_v1.json"
GEO_PACK = ROOT / "data/commander/domain_packs/general_prophecy_geopolitics_pack_v1.json"
REGISTER = ROOT / "scripts/register_general_prophecy_domain_v1.py"
DAILY_LOOP = ROOT / "scripts/run_domain_prophecy_daily_loop_v1.py"


def test_p1_domain_configs_validate() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    for path in (MACRO_CONFIG, GEO_CONFIG):
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=schema)


def test_p1_packs_validate_against_gp_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    gp_schema = json.loads((ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json").read_text(encoding="utf-8"))
    for path in (MACRO_PACK, GEO_PACK):
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=gp_schema)


def test_register_general_prophecy_domain_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REGISTER),
            "--domain-id",
            "general_prophecy_macro_ai",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_domain_daily_loop_dry_run_gp() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(DAILY_LOOP),
            "--domain-id",
            "general_prophecy_geopolitics",
            "--phase",
            "evening",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/domain_prophecy_daily_loop_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("dry_run") is True
    assert doc.get("quality_ok") is True
