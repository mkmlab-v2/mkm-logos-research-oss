# Keywords: isaiah_youtube, reading_pack_slice, showroom, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_showroom_logos_isaiah_youtube_reading_pack_slice_v1.py"
HTML_RUNNER = ROOT / "scripts/build_public_showroom_logos_isaiah_youtube_reading_pack_html_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_logos_isaiah_youtube_reading_pack_slice_v1.schema.json"
BRIDGE = ROOT / "reports/isaiah_youtube_16chapter_mkm_bridge_map_v1_latest.json"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert HTML_RUNNER.is_file()
    assert SCHEMA.is_file()
    assert BRIDGE.is_file()


def test_build_slice(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--no-mirror-artifact",
            "--skip-mvp",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_isaiah_youtube_reading_pack_slice_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc["reading_packs"]) == 3
    assert len(doc["narrative_route_public"]) == 16
    assert len(doc["highlight_presets"]) >= 6
    assert doc["export_gate"]["bridge_map_ok"] is True
    for pack in doc["reading_packs"]:
        assert len(pack["card_excerpt_ko"]) >= 20


def test_build_slice_json_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "slice2.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--no-mirror-artifact",
            "--skip-mvp",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_export_guard_no_forbidden_keys(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.showroom_public_export_guard_v1 import scan_forbidden

    out = tmp_path / "slice3.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--no-mirror-artifact",
            "--skip-mvp",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert scan_forbidden(doc) == []


def test_build_html() -> None:
    r = subprocess.run(
        [sys.executable, str(HTML_RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    html_path = (
        ROOT
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
        / "public_showroom_logos_isaiah_youtube_reading_pack_v1.html"
    )
    html = html_path.read_text(encoding="utf-8")
    assert "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json" in html
    assert "isaiah_youtube_spine_v1" in html
