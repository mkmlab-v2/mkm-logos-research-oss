from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_config_v1.schema.json"
P2_CONFIGS = [
    ROOT / "data/commander/domain_configs/btc_direction_prophecy_config_v1.json",
    ROOT / "data/commander/domain_configs/weather_triplet_prophecy_config_v1.json",
    ROOT / "data/commander/domain_configs/news_observation_prophecy_config_v1.json",
    ROOT / "data/commander/domain_configs/logos_verse_resolution_config_v1.json",
    ROOT / "data/commander/domain_configs/logos_graphrag_insight_config_v1.json",
]
LOGOS_PACK = ROOT / "data/commander/domain_packs/logos_verse_resolution_pack_v1.json"
DAILY_LOOP = ROOT / "scripts/run_domain_prophecy_daily_loop_v1.py"
BTC_EVAL = ROOT / "scripts/run_btc_direction_shadow_eval_v1.py"


@pytest.mark.parametrize("config_path", P2_CONFIGS, ids=[p.stem for p in P2_CONFIGS])
def test_p2_configs_validate(config_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(config_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_logos_verse_pack_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    gp_schema = json.loads((ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json").read_text(encoding="utf-8"))
    doc = json.loads(LOGOS_PACK.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=gp_schema)


def test_btc_shadow_eval_dry_run() -> None:
    proc = subprocess.run(
        [sys.executable, str(BTC_EVAL), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_p2_daily_loop_dry_run_archetypes() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(DAILY_LOOP),
            "--phase",
            "evening",
            "--dry-run",
            "--domain-id",
            "weather_triplet",
            "--domain-id",
            "news_observation",
            "--domain-id",
            "logos_graphrag_insight",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
