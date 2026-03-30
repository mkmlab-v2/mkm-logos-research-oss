# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ENTRY_16 source-hunt summary JSON contract.
# Keywords: entry16, source-hunt, summary, json

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_log.jsonl"
_SUMMARY = _ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_summary.json"


def _rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s.lstrip("\ufeff"))


def test_entry16_source_hunt_summary_contract() -> None:
    assert _SRC.is_file(), f"missing source log: {_SRC}"
    assert _SUMMARY.is_file(), f"missing summary: {_SUMMARY}"
    src_rows = list(_rows(_SRC))
    assert src_rows, "source hunt log must not be empty"

    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    assert summary.get("schema") == "entry16_source_hunt_summary_v1"
    assert summary.get("source_log") == "docs/final/artifacts/entry16_source_hunt_log.jsonl"
    assert int(summary.get("total_sources", -1)) == len(src_rows)
    assert isinstance(summary.get("confidence_counts"), dict)
    assert isinstance(summary.get("witness_counts"), dict)
    assert isinstance(summary.get("access_mode_counts"), dict)
    assert isinstance(summary.get("has_direct_witness"), bool)
    assert summary.get("next_gate") in {
        "promote_entry16_candidate",
        "keep_missing_anchor_until_source_update",
    }


def test_entry16_source_hunt_summary_gate_consistency() -> None:
    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    has_yes = int(summary.get("witness_counts", {}).get("yes", 0)) > 0
    assert bool(summary.get("has_direct_witness")) == has_yes
    expected_gate = "promote_entry16_candidate" if has_yes else "keep_missing_anchor_until_source_update"
    assert summary.get("next_gate") == expected_gate
