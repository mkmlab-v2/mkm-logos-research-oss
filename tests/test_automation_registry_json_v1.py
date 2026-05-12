# Purpose: bitcoin-trading automation_registry.json stays parseable and MKM weekly tasks remain registered.
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "automation_registry.json"

REQUIRED_TASK_KEYS = frozenset({"name", "expected_status", "owner", "criticality"})
MKM_REQUIRED_NAMES = frozenset(
    {
        "\\MKM-KmPhysician-CdsEnvelopeBatch-Weekly",
        "\\MKM-BTrack-BtcWeight-HitRateBundle-Weekly",
        "\\MKM-VaFusionControlIntegrity-Daily",
        "\\MKM-LiveSync-Heartbeat-Pull",
    }
)


def test_automation_registry_json_contract() -> None:
    raw = REGISTRY.read_text(encoding="utf-8")
    doc = json.loads(raw)
    assert doc.get("schema") == "automation_registry_v1"
    tasks = doc.get("tasks")
    assert isinstance(tasks, list) and len(tasks) >= 1

    names: set[str] = set()
    for row in tasks:
        assert isinstance(row, dict)
        missing = REQUIRED_TASK_KEYS - set(row.keys())
        assert not missing, f"task missing keys {sorted(missing)}: {row!r}"
        names.add(str(row["name"]))

    missing_names = MKM_REQUIRED_NAMES - names
    assert not missing_names, f"registry missing tasks: {sorted(missing_names)}"
