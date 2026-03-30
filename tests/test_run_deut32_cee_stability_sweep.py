from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.run_deut32_cee_stability_sweep import main


def test_stability_sweep_generates_report(tmp_path: Path) -> None:
    out = tmp_path / "deut32_cee_stability_sweep_v1.json"
    old = sys.argv
    try:
        sys.argv = ["run_deut32_cee_stability_sweep.py", "--out", str(out)]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "deut32_cee_stability_sweep_v1"
    assert payload["case_count"] >= 3
    assert payload["summary"]["consensus_winner"] in {"sons_of_god", "sons_of_israel"}
