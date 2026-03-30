from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.run_deut32_cee_pilot import main


def test_run_deut32_cee_pilot_generates_report(tmp_path: Path) -> None:
    out = tmp_path / "deut32_cee_pilot_v1.json"
    old = sys.argv
    try:
        sys.argv = ["run_deut32_cee_pilot.py", "--out", str(out)]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "deut32_cee_pilot_v1"
    assert payload["target_ref"] == "Deut.32:8"
    assert len(payload["rows"]) == 2
    assert payload["decision"]["winner_reading_id"] in {"sons_of_god", "sons_of_israel"}
