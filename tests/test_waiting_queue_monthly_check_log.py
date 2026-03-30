# @MKM12-METADATA
# Type: Logic
# Purpose: Validate waiting-queue monthly check log JSONL contract.
# Keywords: waiting-queue, monthly-check, jsonl, ops

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"


def _rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s.lstrip("\ufeff"))


def test_waiting_queue_log_exists_and_has_rows() -> None:
    assert _LOG.is_file(), f"missing log: {_LOG}"
    rows = list(_rows(_LOG))
    assert rows, "waiting queue monthly check log must not be empty"


def test_waiting_queue_log_row_contract() -> None:
    rows = list(_rows(_LOG))
    for i, row in enumerate(rows):
        for key in ("checked_at_utc", "bundle_mode", "cross_ref_test", "runner"):
            assert key in row, f"row[{i}] missing key: {key}"
            assert str(row[key]).strip(), f"row[{i}] empty value: {key}"

        datetime.fromisoformat(str(row["checked_at_utc"]).replace("Z", "+00:00"))
        assert row["bundle_mode"] in {"skip_bundle", "full_bundle"}, f"row[{i}] invalid bundle_mode"
        assert row["cross_ref_test"] == "pass", f"row[{i}] cross_ref_test must be pass"
        assert str(row["runner"]) == "scripts/run_waiting_queue_monthly_check.ps1", (
            f"row[{i}] runner mismatch"
        )

        bundle_test = str(row.get("bundle_test", ""))
        if row["bundle_mode"] == "skip_bundle":
            assert bundle_test in {"skipped", "pass"}, f"row[{i}] invalid skip bundle_test"
        else:
            assert bundle_test == "pass", f"row[{i}] full bundle_test must be pass"


def test_waiting_queue_has_entry16_gate_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "promotion_gate" in r or "promotion_gate_path" in r]
    assert candidates, "at least one log row must include promotion gate fields"

    latest = candidates[-1]
    assert latest.get("source_hunt_summary") == "pass"
    assert str(latest.get("source_hunt_summary_path", "")).endswith(
        "docs\\final\\artifacts\\entry16_source_hunt_summary.json"
    )
    assert latest.get("promotion_gate") == "pass"
    assert str(latest.get("promotion_gate_path", "")).endswith(
        "docs\\final\\artifacts\\entry16_promotion_gate.json"
    )


def test_waiting_queue_has_deadline_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "next_monthly_due_date" in r and "horizon_t90_date" in r]
    assert candidates, "at least one log row must include deadline fields"

    latest = candidates[-1]
    for key in ("next_monthly_due_date", "horizon_t30_date", "horizon_t90_date"):
        value = str(latest.get(key, "")).strip()
        assert value, f"missing {key}"
        datetime.fromisoformat(value)
