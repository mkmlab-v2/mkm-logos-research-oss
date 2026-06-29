from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_commander_interest_signal_inbox_v1 import ingest_inbox  # noqa: E402


def test_inbox_ingest_drains_pending(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox.json"
    log_path = tmp_path / "signals.jsonl"
    inbox.write_text(
        json.dumps(
            {
                "schema": "commander_interest_signal_inbox_v1",
                "items": [
                    {
                        "id": "a1",
                        "status": "pending",
                        "topic_id": "ai_native_systems",
                        "platform": "x",
                        "title": "Test signal",
                        "likes": 10,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    payload = ingest_inbox(inbox_path=inbox, log_path=log_path, bootstrap_example=False, dry_run=False)
    assert payload["ingested_count"] == 1
    assert log_path.is_file()
    doc = json.loads(inbox.read_text(encoding="utf-8"))
    assert doc["items"][0]["status"] == "ingested"


def test_inbox_ingest_dry_run_no_write(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox.json"
    log_path = tmp_path / "signals.jsonl"
    inbox.write_text(
        json.dumps(
            {
                "schema": "commander_interest_signal_inbox_v1",
                "items": [
                    {
                        "id": "b1",
                        "status": "pending",
                        "topic_id": "business_automation",
                        "platform": "linkedin",
                        "title": "Dry run",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    payload = ingest_inbox(inbox_path=inbox, log_path=log_path, bootstrap_example=False, dry_run=True)
    assert payload["pending_found"] == 1
    assert not log_path.exists()
    doc = json.loads(inbox.read_text(encoding="utf-8"))
    assert doc["items"][0]["status"] == "pending"


def test_inbox_ingest_clamps_future_observed_at(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox.json"
    log_path = tmp_path / "signals.jsonl"
    log_path.write_text("", encoding="utf-8")
    future = "2099-01-01T00:00:00Z"
    inbox.write_text(
        json.dumps(
            {
                "schema": "commander_interest_signal_inbox_v1",
                "items": [
                    {
                        "id": "f1",
                        "status": "pending",
                        "topic_id": "ai_native_systems",
                        "platform": "web",
                        "title": "Future dated",
                        "observed_at_utc": future,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ingest_inbox(inbox_path=inbox, log_path=log_path, bootstrap_example=False, dry_run=False)
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    row = json.loads(lines[-1])
    assert row["observed_at_utc"] != future
