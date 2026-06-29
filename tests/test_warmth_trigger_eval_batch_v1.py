from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from scripts.build_warmth_trigger_eval_batch_v1 import run_batch, synthetic_session_from_dose
from scripts.build_warmth_trigger_eval_v1 import _load_json
from scripts.seed_warmth_content_dose_catalog_v1 import main as seed_catalog

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
CATALOG = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_v1.json"
OVERLAY = ROOT / "docs/final/artifacts/epb_sasang_overlay_rules_v1.json"
LWI_SCHEMA = ROOT / "docs/final/schemas/narrative_wellness_index_stub_v1.schema.json"


def test_seed_catalog_has_at_least_20_items(tmp_path: Path):
    seed_catalog()
    catalog = _load_json(CATALOG)
    assert catalog["item_count"] >= 20
    assert len(catalog["items"]) >= 20
    first = catalog["items"][0]
    assert first["schema"] == "warmth_content_dose_v1"
    assert first["research_only"] is True


def test_batch_eval_synthetic_pilot():
    seed_catalog()
    report = run_batch(
        profile=_load_json(PROFILE),
        catalog=_load_json(CATALOG),
        overlay=_load_json(OVERLAY),
    )
    assert report["item_count"] >= 20
    assert report["synthetic_pilot"] is True
    assert "hit_rate" in report["rates"]
    assert sum(report["outcome_counts"].values()) == report["item_count"]


def test_synthetic_session_is_deterministic():
    seed_catalog()
    item = _load_json(CATALOG)["items"][0]
    a = synthetic_session_from_dose(item, 0)
    b = synthetic_session_from_dose(item, 0)
    assert a == b
    assert a["synthetic_pilot"] is True


def test_batch_cli_exit_zero():
    seed_catalog()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_warmth_trigger_eval_batch_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_narrative_wellness_index_stub_schema():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_narrative_wellness_index_stub_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "reports/narrative_wellness_index_stub_v1_latest.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(LWI_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    assert 0 <= payload["index_t"] <= 100
