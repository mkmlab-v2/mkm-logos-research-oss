from __future__ import annotations

from pathlib import Path


def test_ready_ops_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "scripts/record_sasang_human_signoff.py",
        "scripts/check_sasang_ready_drift.py",
        "scripts/run_sasang_ready_rollback_drill.py",
    ):
        assert (root / rel).is_file(), rel
