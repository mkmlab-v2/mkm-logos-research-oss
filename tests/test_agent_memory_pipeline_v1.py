from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPEND_SCRIPT = ROOT / "scripts" / "append_agent_memory_delta_v1.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_agent_memory_evidence_and_conflicts_v1.py"
REBUILD_SCRIPT = ROOT / "scripts" / "rebuild_agent_memory_weekly_v1.py"
LOAD_SCRIPT = ROOT / "scripts" / "load_recent_agent_memory_context_v1.py"


def test_append_and_validate_conflict_downgrades_confidence(tmp_path: Path) -> None:
    memory = tmp_path / "memory.jsonl"
    memory_a = tmp_path / "memory_a.jsonl"
    memory_b = tmp_path / "memory_b.jsonl"
    context = tmp_path / "context.json"
    validation = tmp_path / "validation.json"
    central = tmp_path / "central.md"
    central.write_text("seed", encoding="utf-8")

    proc_append = subprocess.run(
        [
            "py",
            str(APPEND_SCRIPT),
            "--memory-jsonl",
            str(memory),
            "--write-combined",
            "--track-memory-jsonl-a",
            str(memory_a),
            "--track-memory-jsonl-b",
            str(memory_b),
            "--central-memory-md",
            str(central),
            "--mission",
            "production deploy_now",
            "--state",
            "done",
            "--risk",
            "medium",
            "--next",
            "auto_live",
            "--track",
            "B",
            "--context-json",
            str(context),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_append.returncode == 0, proc_append.stdout + proc_append.stderr

    row = json.loads(memory.read_text(encoding="utf-8").splitlines()[-1])
    assert row["confidence"] == "C"
    assert row["conflict_flags"]["has_conflict"] is True
    split_row = json.loads(memory_b.read_text(encoding="utf-8").splitlines()[-1])
    assert split_row["track"] == "B"

    proc_validate = subprocess.run(
        [
            "py",
            str(VALIDATE_SCRIPT),
            "--memory-jsonl",
            str(memory),
            "--memory-jsonl-a",
            str(memory_a),
            "--memory-jsonl-b",
            str(memory_b),
            "--output-json",
            str(validation),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_validate.returncode == 0, proc_validate.stdout + proc_validate.stderr
    doc = json.loads(validation.read_text(encoding="utf-8"))
    assert doc["status"] == "HOLD_REVIEW"


def test_weekly_rebuild_promotes_hot_and_builds_compact(tmp_path: Path) -> None:
    memory = tmp_path / "memory.jsonl"
    memory_a = tmp_path / "memory_a.jsonl"
    memory_b = tmp_path / "memory_b.jsonl"
    hot = tmp_path / "hot.jsonl"
    summary = tmp_path / "summary.json"
    compact = tmp_path / "compact.json"

    rows = [
        {
            "schema": "agent_memory_delta_v1",
            "ts_utc": "2099-01-01T00:00:00Z",
            "mission": "safe",
            "state": "ok",
            "evidence_path": ["docs/final/CENTRAL_AGENT_MEMORY_V1.md"],
            "risk": "low",
            "next": "continue",
            "track": "B",
            "confidence": "A",
            "reproducibility_score": 1,
            "conflict_flags": {"has_conflict": False},
        },
        {
            "schema": "agent_memory_delta_v1",
            "ts_utc": "2099-01-01T00:00:00Z",
            "mission": "bad",
            "state": "warn",
            "evidence_path": [],
            "risk": "high",
            "next": "hold",
            "track": "B",
            "confidence": "C",
            "conflict_flags": {"has_conflict": True},
        },
    ]
    memory.write_text("", encoding="utf-8")
    memory_a.write_text("", encoding="utf-8")
    memory_b.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    proc = subprocess.run(
        [
            "py",
            str(REBUILD_SCRIPT),
            "--memory-jsonl",
            str(memory),
            "--memory-jsonl-a",
            str(memory_a),
            "--memory-jsonl-b",
            str(memory_b),
            "--combined-mirror-jsonl",
            str(memory),
            "--hot-jsonl",
            str(hot),
            "--summary-json",
            str(summary),
            "--compact-json",
            str(compact),
            "--ttl-days",
            "7",
            "--compact-limit",
            "20",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary_doc = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_doc["status"] == "PASS"
    assert summary_doc["hot_rows"] == 1
    compact_doc = json.loads(compact.read_text(encoding="utf-8"))
    assert compact_doc["line_count"] >= 1


def test_loader_dedups_combined_and_split_rows(tmp_path: Path) -> None:
    combined = tmp_path / "combined.jsonl"
    track_a = tmp_path / "a.jsonl"
    track_b = tmp_path / "b.jsonl"
    out = tmp_path / "context.json"
    row = {
        "schema": "agent_memory_delta_v1",
        "ts_utc": "2099-01-01T00:00:00Z",
        "mission": "m1",
        "state": "s1",
        "source": "unit",
        "track": "B",
        "risk": "low",
        "next": "n1",
        "confidence": "A",
    }
    combined.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    track_b.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    track_a.write_text("", encoding="utf-8")

    proc = subprocess.run(
        [
            "py",
            str(LOAD_SCRIPT),
            "--memory-jsonl",
            str(combined),
            "--memory-jsonl-a",
            str(track_a),
            "--memory-jsonl-b",
            str(track_b),
            "--recent-n",
            "3",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["rows_seen_before_dedup"] == 2
    assert doc["rows_seen_after_dedup"] == 1
