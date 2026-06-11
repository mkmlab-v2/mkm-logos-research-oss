"""[HYPO] open-bench research sweep schema smoke."""
from __future__ import annotations

import json
from pathlib import Path


def test_research_sweep_latest_schema() -> None:
    path = Path("reports/compression_open_bench_research_sweep_v1_latest.json")
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_open_bench_research_sweep_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["research_only"] is True
    assert doc["chain_ok"] is True
    assert len(doc["variants"]) >= 6
    baseline = next(v for v in doc["variants"] if v["variant_id"] == "baseline_routed_economy")
    assert baseline["raw"]["saving_pct_display"] == 9.36
