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
_QUERY_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_vector_ann_lite_query_result_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_ANN_LITE_BUILD_REPORT_V1_CONTRACT.json"
_QUERY = _ROOT / "scripts" / "query_logos_vector_index_ann_lite_v1.py"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()
    assert _QUERY_SCHEMA.is_file()
    assert _QUERY.is_file()
    meta = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert meta.get("artifact_schema") == "logos_vector_index_ann_lite_build_report_v1"
    assert meta.get("query_runner") == "scripts/query_logos_vector_index_ann_lite_v1.py"


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


def test_sentence_transformers_blocked_when_policy_stub(tmp_path: Path) -> None:
    policy = tmp_path / "pol_st.json"
    policy.write_text(
        json.dumps(
            {"schema": "logos_vector_index_policy_v1", "version": "1.0.0", "status": "stub"},
            indent=2,
        ),
        encoding="utf-8",
    )
    verses = tmp_path / "v_st.json"
    verses.write_text(json.dumps([{"verse_id": "x"}], indent=2), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(policy),
            "--verse-json",
            str(verses),
            "--embedding-backend",
            "sentence_transformers",
            "--sentence-transformer-model",
            "dummy-model",
            "--report-json",
            str(tmp_path / "r.json"),
            "--sqlite-out",
            str(tmp_path / "s.sqlite"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 5


def test_stream_parse_small_file(tmp_path: Path) -> None:
    pytest.importorskip("ijson")
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    policy = tmp_path / "pol_ij.json"
    policy.write_text(
        json.dumps(
            {"schema": "logos_vector_index_policy_v1", "version": "1.0.0", "status": "stub"},
            indent=2,
        ),
        encoding="utf-8",
    )
    verses = tmp_path / "v_ij.json"
    verses.write_text(
        json.dumps([{"verse_id": "stream:1"}, {"verse_id": "stream:2"}], indent=2),
        encoding="utf-8",
    )
    report = tmp_path / "rep_ij.json"
    sqlite_out = tmp_path / "ij.sqlite"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(policy),
            "--verse-json",
            str(verses),
            "--stream",
            "--vector-dim",
            "16",
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
    assert doc.get("verse_source", {}).get("stream_parsing_used") is True


def test_query_cli_fixture(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    qschema = json.loads(_QUERY_SCHEMA.read_text(encoding="utf-8"))

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
        json.dumps([{"verse_id": "fixture:v1", "text": "alpha"}], indent=2),
        encoding="utf-8",
    )
    sqlite_out = tmp_path / "stub.sqlite"
    report = tmp_path / "report.json"

    b = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(policy),
            "--verse-json",
            str(verses),
            "--vector-dim",
            "16",
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
    assert b.returncode == 0, b.stderr

    cp = subprocess.run(
        [
            sys.executable,
            str(_QUERY),
            "--sqlite",
            str(sqlite_out),
            "--query",
            "probe text",
            "--top-k",
            "3",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    jsonschema.Draft7Validator(qschema).validate(doc)
    assert doc.get("schema") == "logos_vector_ann_lite_query_result_v1"
    assert len(doc.get("top_k", [])) >= 1
