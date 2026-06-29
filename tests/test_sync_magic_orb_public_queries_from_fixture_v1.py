"""Sync magic orb public queries fixture + job preset SSOT."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts/sync_magic_orb_public_queries_from_fixture_v1.py"
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_queries_v1.json"
JOB_HASH = "dc73c2c367199e48"
JOB_BY_QUERY = ROOT / f"projects/mkm/mkm-life/public/data/magic_orb_insight_by_query/{JOB_HASH}.json"
PRESET_TS = ROOT / "projects/mkm/mkm-life/lib/magic-orb-query-presets-v1.ts"


def test_sync_magic_orb_public_queries_includes_job_row() -> None:
    proc = subprocess.run(
        [sys.executable, str(SYNC)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(PUBLIC.read_text(encoding="utf-8"))
    job = next((it for it in doc.get("items") or [] if it.get("id") == "job_suffering_reason"), None)
    assert job is not None
    assert job.get("query_ko") == "욥이 고난을 받은 이유"
    assert job.get("query_key_hint") == JOB_HASH
    assert job.get("consumer_query_ko")


def test_job_preset_ts_matches_fixture_hash() -> None:
    text = PRESET_TS.read_text(encoding="utf-8")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    job = next(it for it in fixture["items"] if it["id"] == "job_suffering_reason")
    assert JOB_HASH in text
    assert job["query_ko"] in text
    assert "magic_orb_insight_by_query" in text
    assert "JOB_SUFFERING_REASON_QUERY_HASH" in text


def test_job_by_query_public_four_slot_hold() -> None:
    assert JOB_BY_QUERY.is_file(), "run chain with --sync-public-by-query first"
    doc = json.loads(JOB_BY_QUERY.read_text(encoding="utf-8"))
    assert doc.get("schema") == "magic_orb_question_insight_v1"
    fs = doc.get("four_slot_response_v1") or {}
    assert fs.get("schema_version") == "four_slot_response_v1"
    assert (fs.get("enforcement") or {}).get("send_gate") == "HOLD"
