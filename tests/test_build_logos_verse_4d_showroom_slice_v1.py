# Keywords: build_logos_verse_4d_showroom_slice_v1, logos, NON_GATING, v1_core_subset

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_logos_verse_4d_showroom_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_verse_4d_showroom_slice_v1.schema.json"
FIXTURE_DIR = ROOT / "tests/data/logos_verse_4d_showroom_slice_v1"

BOUNDARY_KO = (
    "정경 31,102절 SSOT 대비 verse_decoded_v2(BHS+SBLGNT)에 없는 2,361절; "
    "Track B 구절 4D·그래프·렉시콘 백투영은 28,741행(v1_core_subset) 범위."
)
BOUNDARY_EN = (
    "MT canon 31,102-verse SSOT minus 2,361 verses absent from verse_decoded_v2 (BHS+SBLGNT) "
    "= 28,741-verse BHS+SBLGNT Track B map (v1_core_subset)."
)


def _fixture(name: str) -> Path:
    return FIXTURE_DIR / name


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    for name in (
        "coverage_diff_min.json",
        "medoids_min.json",
        "os_compare_min.json",
        "corpus_min.json",
        "contract_min.json",
    ):
        assert _fixture(name).is_file()


def test_build_slice_with_fixtures(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--coverage-diff",
            str(_fixture("coverage_diff_min.json")),
            "--medoids",
            str(_fixture("medoids_min.json")),
            "--os-compare",
            str(_fixture("os_compare_min.json")),
            "--corpus",
            str(_fixture("corpus_min.json")),
            "--contract",
            str(_fixture("contract_min.json")),
            "--out-json",
            str(out),
            "--no-mirror",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_verse_4d_showroom_slice_v1"
    assert doc["subset_id"] == "v1_core_subset"
    assert doc["boundary_sentence_ko"] == BOUNDARY_KO
    assert doc["boundary_sentence_en"] == BOUNDARY_EN
    assert doc["coverage"]["full_canon_verse_count"] == 31102
    assert doc["coverage"]["verse_decoded_v2_count"] == 28741
    assert doc["coverage"]["gap_count"] == 2361
    assert doc["coverage"]["phase1_rows_dropped"] == 0
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["disclaimer"]["ready_for_external_send"] is False
    assert doc["track_wall"]["live_trading_trigger"] is False
    assert len(doc["sample_findings"]["top_medoids"]) == 2
    assert doc["sample_findings"]["phase4_null_vs_canon"]["sample_size_small"] is True


def test_build_slice_jsonschema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "slice2.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--coverage-diff",
            str(_fixture("coverage_diff_min.json")),
            "--medoids",
            str(_fixture("medoids_min.json")),
            "--os-compare",
            str(_fixture("os_compare_min.json")),
            "--corpus",
            str(_fixture("corpus_min.json")),
            "--contract",
            str(_fixture("contract_min.json")),
            "--out-json",
            str(out),
            "--no-mirror",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


@pytest.mark.skipif(
    not (ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json").is_file(),
    reason="production artifacts missing",
)
def test_build_slice_default_repo_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "repo_slice.json"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out), "--no-mirror"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["coverage"]["gap_count"] == 2361
    assert doc["boundary_sentence_ko"] == BOUNDARY_KO
    assert "proven_cosmic_os" in doc["factory_demo"]["forbidden_claims"]
