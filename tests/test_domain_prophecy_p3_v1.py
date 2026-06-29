from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_config_v1.schema.json"
P3_CONFIGS = [
    ROOT / "data/commander/domain_configs/mkmlife_moment_config_v1.json",
    ROOT / "data/commander/domain_configs/personadiary_moment_config_v1.json",
    ROOT / "data/commander/domain_configs/clinical_cohort_hypo_config_v1.json",
    ROOT / "data/commander/domain_configs/jemaai_showroom_obs_config_v1.json",
]
P3_PACKS = [
    ROOT / "data/commander/domain_packs/mkmlife_moment_pack_v1.json",
    ROOT / "data/commander/domain_packs/personadiary_moment_pack_v1.json",
    ROOT / "data/commander/domain_packs/clinical_cohort_hypo_pack_v1.json",
]
DAILY_LOOP = ROOT / "scripts/run_domain_prophecy_daily_loop_v1.py"
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"


@pytest.mark.parametrize("config_path", P3_CONFIGS, ids=[p.stem for p in P3_CONFIGS])
def test_p3_configs_validate(config_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(config_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


@pytest.mark.parametrize("pack_path", P3_PACKS, ids=[p.stem for p in P3_PACKS])
def test_p3_packs_validate(pack_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    gp_schema = json.loads((ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json").read_text(encoding="utf-8"))
    doc = json.loads(pack_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=gp_schema)


def test_p3_registry_active() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = {r["domain_id"]: r for r in registry.get("domains") or []}
    for domain_id in ("mkmlife_moment", "personadiary_moment", "clinical_cohort_hypo", "jemaai_showroom_obs"):
        row = rows[domain_id]
        assert row.get("phase") == "P3"
        assert row.get("status") == "active"
        assert row.get("config_path")


def test_p3_daily_loop_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(DAILY_LOOP),
            "--phase",
            "evening",
            "--dry-run",
            "--domain-id",
            "mkmlife_moment",
            "--domain-id",
            "personadiary_moment",
            "--domain-id",
            "jemaai_showroom_obs",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_personadiary_gate_offline() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/check_personadiary_moment_domain_gate_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
