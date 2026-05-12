from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_approval_ticket_v1.schema.json"


def _ticket(
    *,
    ticket_id: str = "test-ticket-001",
    scope_allow: list[str] | None = None,
    max_runs_per_day: int = 0,
) -> dict:
    return {
        "schema": "mkm_approval_ticket_v1",
        "ticket_id": ticket_id,
        "title": "Test",
        "valid_from_utc": "2020-01-01T00:00:00Z",
        "valid_until_utc": "2099-12-31T23:59:59Z",
        "approved": True,
        "approved_by": "tester",
        "approved_at_utc": "2026-05-12T00:00:00Z",
        "scope_allow": scope_allow or ["allowed_tag"],
        "scope_deny": ["live_trading"],
        "execution_caps": {
            "allow_live_trading": False,
            "allow_github_push": False,
            "allow_cost_incurring_api": False,
            "max_runs_per_day": max_runs_per_day,
        },
    }


def test_preflight_go(tmp_path):
    t = tmp_path / "ticket.json"
    t.write_text(json.dumps(_ticket()), encoding="utf-8")
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_mkm_approval_ticket_preflight_v1.py"),
            "--ticket-json",
            str(t),
            "--schema-json",
            str(SCHEMA),
            "--out",
            str(out),
            "--execution-tag",
            "allowed_tag",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"] == "GO"


def test_preflight_no_go_wrong_tag(tmp_path):
    t = tmp_path / "ticket.json"
    t.write_text(json.dumps(_ticket()), encoding="utf-8")
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_mkm_approval_ticket_preflight_v1.py"),
            "--ticket-json",
            str(t),
            "--schema-json",
            str(SCHEMA),
            "--out",
            str(out),
            "--execution-tag",
            "other_tag",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"] == "NO_GO"
    assert "execution_tag_not_in_scope_allow" in doc["reasons"]


def test_preflight_max_runs(tmp_path):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tid = "cap-test"
    t = tmp_path / "ticket.json"
    t.write_text(json.dumps(_ticket(ticket_id=tid, max_runs_per_day=1)), encoding="utf-8")
    counts = tmp_path / "counts.json"
    counts.write_text(
        json.dumps({"schema": "mkm_approval_ticket_run_counts_v1", "counts": {f"{tid}|{day}": 1}}),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_mkm_approval_ticket_preflight_v1.py"),
            "--ticket-json",
            str(t),
            "--schema-json",
            str(SCHEMA),
            "--out",
            str(out),
            "--execution-tag",
            "allowed_tag",
            "--runs-state-json",
            str(counts),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "max_runs_per_day_exceeded" in doc["reasons"]


def test_bump_run_count(tmp_path):
    tid = "bump-test"
    t = tmp_path / "ticket.json"
    t.write_text(json.dumps(_ticket(ticket_id=tid, max_runs_per_day=9)), encoding="utf-8")
    counts = tmp_path / "counts.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/bump_mkm_approval_ticket_run_count_v1.py"),
            "--ticket-json",
            str(t),
            "--runs-state-json",
            str(counts),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    st = json.loads(counts.read_text(encoding="utf-8"))
    assert len(st["counts"]) == 1
    assert next(iter(st["counts"].values())) == 1
