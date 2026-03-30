# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ENTRY_16 source-ingest helper CLI behavior.
# Keywords: entry16, source-hunt, cli, rejudge

from __future__ import annotations

import json
import sys
from pathlib import Path

import scripts.add_entry16_source_and_rejudge as cli


def _base_argv() -> list[str]:
    return [
        "add_entry16_source_and_rejudge.py",
        "--source-url",
        "https://example.org/new-source",
        "--source-title",
        "Example source",
        "--publisher-or-host",
        "Example host",
        "--resource-type",
        "transcription_line_anchor",
        "--djd-volume",
        "DJD XVI",
        "--page-range",
        "p.291-293",
        "--fragment-sigla",
        "4Q117 frg.1",
        "--line-anchor",
        "frg.1 lines 1-6",
        "--extant-verses-claim",
        "Esr 4:2-6 only",
        "--witness",
        "no",
        "--evidence-quote",
        "No Ezra 2:54",
        "--confidence",
        "med",
        "--access-mode",
        "public",
        "--last-checked-utc",
        "2026-03-30T00:00:00Z",
    ]


def test_dry_run_does_not_write_log(tmp_path: Path, monkeypatch, capsys) -> None:
    log_path = tmp_path / "entry16_source_hunt_log.jsonl"
    summary_path = tmp_path / "entry16_source_hunt_summary.json"
    monkeypatch.setattr(cli, "LOG", log_path)
    monkeypatch.setattr(cli, "SUMMARY", summary_path)
    monkeypatch.setattr(sys, "argv", _base_argv() + ["--dry-run"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "DRY-RUN: no file updates" in out
    assert not log_path.exists()


def test_duplicate_url_raises_system_exit(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "entry16_source_hunt_log.jsonl"
    summary_path = tmp_path / "entry16_source_hunt_summary.json"
    existing = {"source_url": "https://example.org/new-source"}
    log_path.write_text(json.dumps(existing) + "\n", encoding="utf-8")

    monkeypatch.setattr(cli, "LOG", log_path)
    monkeypatch.setattr(cli, "SUMMARY", summary_path)
    monkeypatch.setattr(sys, "argv", _base_argv())

    try:
        cli.main()
        assert False, "expected SystemExit for duplicate URL"
    except SystemExit as e:
        assert "duplicate source_url" in str(e)


def test_pause_guard_blocks_public_unknown_without_override(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "entry16_source_hunt_log.jsonl"
    summary_path = tmp_path / "entry16_source_hunt_summary.json"
    summary_path.write_text(
        json.dumps({"action_recommendation": "pause_hunting_until_new_primary_source"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "LOG", log_path)
    monkeypatch.setattr(cli, "SUMMARY", summary_path)
    monkeypatch.setattr(sys, "argv", _base_argv() + ["--dry-run"])

    try:
        cli.main()
        assert False, "expected SystemExit for paused ingest"
    except SystemExit as e:
        assert "public no/unknown source ingest is paused" in str(e)

