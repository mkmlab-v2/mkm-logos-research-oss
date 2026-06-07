# Keywords: dss, etcbc, research_only, B-track

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DSS = ROOT / "projects/dss-4d-ingest"


def test_dss_token_pilot_dry_run_produces_metadata_rows() -> None:
    out = ROOT / "reports/tmp_dss_token_dry_run/dss_tokens_pilot_manifest_tf4.ndjson"
    if out.is_file():
        out.unlink()
    r = subprocess.run(
        [
            sys.executable,
            str(DSS / "run_dss_token_pilot.py"),
            "--manifest",
            "dss_pilot_manifest_tf4.json",
            "--dry-run",
            "--force-manifest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out.is_file()
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 200
    assert all("work" in row and "token_index" in row for row in rows)
    assert all("text" not in row and "surface" not in row for row in rows)


def test_dss_token_pilot_writes_outputs_non_smoke() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(DSS / "run_dss_token_pilot.py"),
            "--manifest",
            "dss_pilot_manifest_tf4.json",
            "--force-manifest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    primary = DSS / "outputs/dss_tokens_pilot_manifest_tf4.ndjson"
    alias = DSS / "outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson"
    assert primary.is_file()
    assert alias.is_file()
    count = sum(1 for line in primary.read_text(encoding="utf-8").splitlines() if line.strip())
    assert count == 200
    assert count > 5


def test_fusion_join_quality_smoke_with_apocrypha_ext2() -> None:
    dss_ndjson = DSS / "outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson"
    apo_ndjson = DSS / "outputs/apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson"
    if not dss_ndjson.is_file():
        subprocess.run(
            [sys.executable, str(DSS / "run_dss_token_pilot.py"), "--force-manifest"],
            cwd=str(ROOT),
            check=True,
        )
    assert apo_ndjson.is_file(), "apocrypha ext2 weighted must exist (A-lane rebuild)"
    out = DSS / "outputs/fusion_join_quality_research_smoke_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(DSS / "judge_fusion_join_quality.py"),
            "--dss-ndjson",
            str(dss_ndjson),
            "--apocrypha-ndjson",
            str(apo_ndjson),
            "--min-overlap-tokens",
            "5",
            "--min-overlap-ratio-dss",
            "0.005",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("status") == "PASS"
    assert doc.get("overlap_token_estimate", 0) >= 5


def test_setup_etcbc_dss_data_pointer_report() -> None:
    out = ROOT / "reports/etcbc_dss_data_pointer_latest.json"
    r = subprocess.run(
        [sys.executable, str(DSS / "setup_etcbc_dss_data_v1.py"), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 1)
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "etcbc_dss_data_pointer_v1"
    assert "acquisition_steps" in doc
