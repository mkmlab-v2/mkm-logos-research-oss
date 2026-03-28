"""Pytest hooks: Dual Regime integrity Fact-Lock report (workspace ``backtest_results/``)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# tests/ -> bitcoin-trading/ -> projects/ -> workspace
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_REPORT_PATH = _WORKSPACE_ROOT / "backtest_results" / "REGIME_INTEGRITY_REPORT.json"

_REGIME_CASES: list[dict[str, Any]] = []


def pytest_runtest_logreport(report: Any) -> None:
    """Collect outcomes for dual-regime / regime_integrity tests."""
    if report.when != "call":
        return
    nodeid = getattr(report, "nodeid", "") or ""
    if "dual_regime" not in nodeid and "regime_integrity" not in nodeid:
        return
    duration = getattr(report, "duration", None)
    _REGIME_CASES.append(
        {
            "nodeid": nodeid,
            "outcome": report.outcome,
            "duration_sec": round(duration, 4) if duration is not None else None,
        }
    )


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Write Fact-Lock summary after test session (even if no regime tests ran)."""
    if not _REGIME_CASES:
        return
    passed = sum(1 for c in _REGIME_CASES if c["outcome"] == "passed")
    failed = sum(1 for c in _REGIME_CASES if c["outcome"] == "failed")
    skipped = sum(1 for c in _REGIME_CASES if c["outcome"] == "skipped")
    payload = {
        "report_type": "REGIME_INTEGRITY_FACT_LOCK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(_WORKSPACE_ROOT),
        "pytest_exitstatus": exitstatus,
        "policy_ssot": str(_WORKSPACE_ROOT / "data" / "regimes" / "regime_fusion_policy.json"),
        "summary": {
            "total": len(_REGIME_CASES),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "cases": _REGIME_CASES,
    }
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
