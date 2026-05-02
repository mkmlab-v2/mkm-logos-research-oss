# @MKM12-METADATA
# Type: Logic
# Purpose: Logos vector index ANN lite (hash stub + sqlite) regression.
# Keywords: logos, track_b, vector_index, ann

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_logos_vector_index_ann_lite_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_vector_index_ann_lite_build_report_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_ANN_LITE_BUILD_REPORT_V1_CONTRACT.json"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()
    meta = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert meta.get("artifact_schema") == "logos_vector_index_ann_lite_build_report_v1"


def test_runner_fixture(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))

    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "schema": "logos_vector_index_policy_v1",
                "version": "1.0.0",
                "status": "stub",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    verses = tmp_path / "verses.json"
    verses.write_text(
        json.dumps(
            [
                {"verse_id": "fixture:v1", "text": "alpha"},
                {"verse_id": "fixture:v2", "text": "beta"},
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    sqlite_out = tmp_path / "stub.sqlite"

    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(policy),
            "--verse-json",
            str(verses),
            "--max-verses",
            "10",
            "--vector-dim",
            "32",
            "--report-json",
            str(report),
            "--sqlite-out",
            str(sqlite_out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr

    doc = json.loads(report.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("schema") == "logos_vector_index_ann_lite_build_report_v1"
    assert doc.get("embedding_mode") == "hash_stub_v1"
    assert doc.get("rows_written") == 2
    assert doc.get("vector_dim") == 32

    con = sqlite3.connect(str(sqlite_out))
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM logos_vec_stub")
        assert cur.fetchone()[0] == 2
    finally:
        con.close()
