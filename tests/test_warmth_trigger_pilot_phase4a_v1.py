from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from scripts.build_warmth_trigger_pilot_pack_v1 import build_pack, _catalog_readiness
from scripts.check_warmth_trigger_pilot_readiness_v1 import evaluate_readiness
from scripts.seed_warmth_content_dose_catalog_curated_v1 import main as seed_curated

ROOT = Path(__file__).resolve().parents[1]
DOSE_SCHEMA = ROOT / "docs/final/schemas/warmth_content_dose_v1.schema.json"
PROTOCOL_SCHEMA = ROOT / "docs/final/schemas/warmth_trigger_pilot_protocol_v1.schema.json"
PROTOCOL = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_protocol_v1.example.json"
CATALOG = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_curated_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_curated_catalog_seed_and_dose_schema():
    seed_curated()
    catalog = _load(CATALOG)
    dose_schema = _load(DOSE_SCHEMA)
    assert catalog["item_count"] >= 10
    for item in catalog["items"]:
        jsonschema.validate(item["dose_item"], dose_schema)
        assert item["curator_review"]["status"] == "approved"
        assert item["dose_item"]["provenance"]["source"] == "manual_curation"


def test_protocol_fixture_schema():
    payload = _load(PROTOCOL)
    schema = _load(PROTOCOL_SCHEMA)
    jsonschema.validate(payload, schema)
    assert payload["target_n_participants"] >= 30


def test_pilot_pack_enrollment_ready():
    seed_curated()
    catalog = _load(CATALOG)
    protocol = _load(PROTOCOL)
    pack = build_pack(catalog=catalog, protocol=protocol)
    assert pack["pilot_ready_for_enrollment"] is True
    assert pack["catalog_readiness"]["item_count"] >= 10
    readiness = evaluate_readiness(pack)
    assert readiness["enrollment_ready"] is True
    assert readiness["human_data_collection_complete"] is False


def test_build_pack_cli_writes_enrollment_jsonl():
    seed_curated()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_warmth_trigger_pilot_pack_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    enrollment = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_enrollment_template_v1.jsonl"
    lines = enrollment.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 30


def test_readiness_strict_exit_zero_after_pack():
    seed_curated()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_warmth_trigger_pilot_pack_v1.py")],
        cwd=ROOT,
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_warmth_trigger_pilot_readiness_v1.py"),
            "--strict",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_catalog_readiness_counts():
    seed_curated()
    ready = _catalog_readiness(_load(CATALOG))
    assert ready["approved_count"] == ready["item_count"]
    assert ready["all_approved"] is True
