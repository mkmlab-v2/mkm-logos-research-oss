"""Report ledger stub fixture — hub /hub/reports P2."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "projects/no1kmedi/public/data/universe_hub_report_ledger_stub_v1.json"
REPORTS_PAGE = ROOT / "projects/no1kmedi/src/app/hub/reports/page.tsx"


def test_report_ledger_fixture_schema():
    assert FIXTURE.is_file()
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert doc["schema"] == "universe_hub_report_ledger_stub_v1"
    assert doc.get("research_only") is True
    assert len(doc.get("entries") or []) >= 1
    for banned in ("47.5%", "56.5%"):
        assert banned not in FIXTURE.read_text(encoding="utf-8")


def test_reports_page_loads_ledger_component():
    text = REPORTS_PAGE.read_text(encoding="utf-8")
    assert "UniverseReportsLedgerStubV2" in text
    assert "universe_hub_report_ledger_stub_v1.json" in text
