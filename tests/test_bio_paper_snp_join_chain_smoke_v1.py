# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke join gate + apply + mapping export (no network).
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
_SIDECAR = _ROOT / "docs" / "final" / "artifacts" / "bio_measured_labels_paper_snp_sidecar_v1.json"
_MAPPING = _ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_mapping_v1.csv"
_SAMPLES = _ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_samples_v1.csv"
_APPLY = _SCRIPTS / "apply_bio_paper_snp_sidecar_to_samples_v1.py"
_EXPORT_MAP = _SCRIPTS / "export_bio_sample_paper_pmid_mapping_from_cohort_v1.py"
_COVERAGE = _SCRIPTS / "check_bio_paper_snp_mapping_coverage_v1.py"
_CHAIN = _SCRIPTS / "run_bio_paper_snp_sidecar_export_and_apply_v1.py"


def test_check_join_gate_ok() -> None:
    sys.path.insert(0, str(_SCRIPTS))
    from spec_bio_sample_paper_snp_join_gate_v1 import check_join_gate

    code, msg = check_join_gate(_MAPPING, _SIDECAR)
    assert code == 0, msg


def test_apply_paper_snp_sidecar_smoke(tmp_path: Path) -> None:
    out_csv = tmp_path / "joined.csv"
    out_rep = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(_APPLY),
        "--samples-csv",
        str(_SAMPLES),
        "--mapping-csv",
        str(_MAPPING),
        "--sidecar-json",
        str(_SIDECAR),
        "--output-csv",
        str(out_csv),
        "--output-report",
        str(out_rep),
    ]
    subprocess.check_call(cmd, cwd=str(_ROOT))
    rows = list(csv.DictReader(io.StringIO(out_csv.read_text(encoding="utf-8"))))
    assert len(rows) == 1
    r = rows[0]
    assert r["sample_id"] == "smoke_join_a"
    assert r["paper_pmid"] == "30376909"
    assert "rs10937331" in (r.get("paper_snp_ids_final_v3") or "")


def test_check_mapping_coverage_fixture(tmp_path: Path) -> None:
    out = tmp_path / "cov.json"
    subprocess.check_call(
        [
            sys.executable,
            str(_COVERAGE),
            "--cohort-csv",
            str(_SAMPLES),
            "--mapping-csv",
            str(_MAPPING),
            "--output-json",
            str(out),
        ],
        cwd=str(_ROOT),
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bio_paper_snp_mapping_coverage_v1"
    assert doc.get("coverage_ratio") == 1.0
    assert doc.get("cohort_distinct_sample_id") == 1


def test_chain_mapping_coverage_min_blocks_partial_cohort(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort2.csv"
    cohort.write_text("sample_id,n\na,1\nb,2\n", encoding="utf-8")
    mapping = tmp_path / "map_partial.csv"
    mapping.write_text("sample_id,pmid\na,30376909\n", encoding="utf-8")
    out_csv = tmp_path / "blocked.csv"
    out_rep = tmp_path / "blocked.json"
    cov = tmp_path / "cov_block.json"
    cmd = [
        sys.executable,
        str(_CHAIN),
        "--skip-export",
        "--samples-csv",
        str(cohort),
        "--mapping-csv",
        str(mapping),
        "--sidecar-json",
        str(_SIDECAR),
        "--output-csv",
        str(out_csv),
        "--output-report",
        str(out_rep),
        "--mapping-coverage-min",
        "0.75",
        "--coverage-output-json",
        str(cov),
    ]
    r = subprocess.run(cmd, cwd=str(_ROOT))
    assert r.returncode == 2


def test_chain_mapping_coverage_min_passes_and_applies(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort2.csv"
    cohort.write_text("sample_id,n\na,1\nb,2\n", encoding="utf-8")
    mapping = tmp_path / "map_partial.csv"
    mapping.write_text("sample_id,pmid\na,30376909\n", encoding="utf-8")
    out_csv = tmp_path / "joined2.csv"
    out_rep = tmp_path / "rep2.json"
    subprocess.check_call(
        [
            sys.executable,
            str(_CHAIN),
            "--skip-export",
            "--samples-csv",
            str(cohort),
            "--mapping-csv",
            str(mapping),
            "--sidecar-json",
            str(_SIDECAR),
            "--output-csv",
            str(out_csv),
            "--output-report",
            str(out_rep),
            "--mapping-coverage-min",
            "0.5",
        ],
        cwd=str(_ROOT),
    )
    rows = list(csv.DictReader(io.StringIO(out_csv.read_text(encoding="utf-8"))))
    assert len(rows) == 2
    by_id = {r["sample_id"]: r for r in rows}
    assert by_id["a"]["paper_pmid"] == "30376909"
    assert by_id["b"].get("paper_pmid") == ""


def test_chain_full_fixture_with_coverage_min_one(tmp_path: Path) -> None:
    out_csv = tmp_path / "jf.csv"
    out_rep = tmp_path / "jf.json"
    subprocess.check_call(
        [
            sys.executable,
            str(_CHAIN),
            "--skip-export",
            "--samples-csv",
            str(_SAMPLES),
            "--mapping-csv",
            str(_MAPPING),
            "--sidecar-json",
            str(_SIDECAR),
            "--output-csv",
            str(out_csv),
            "--output-report",
            str(out_rep),
            "--mapping-coverage-min",
            "1.0",
        ],
        cwd=str(_ROOT),
    )
    rows = list(csv.DictReader(io.StringIO(out_csv.read_text(encoding="utf-8"))))
    assert len(rows) == 1


def test_export_sample_pmid_mapping_from_cohort(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("sample_id,paper_pmid,extra\nm1,30376909,x\n", encoding="utf-8")
    out_map = tmp_path / "mapping.csv"
    subprocess.check_call(
        [
            sys.executable,
            str(_EXPORT_MAP),
            "--input-csv",
            str(cohort),
            "--output-csv",
            str(out_map),
        ],
        cwd=str(_ROOT),
    )
    body = out_map.read_text(encoding="utf-8").strip().splitlines()
    assert body[0] == "sample_id,pmid"
    assert body[1] == "m1,30376909"
