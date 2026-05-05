from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_symbolic_revalidation_report_v1.py"


def test_build_revalidation_report_smoke(tmp_path: Path) -> None:
    backtest = tmp_path / "bt.json"
    rows = []
    for i in range(1, 11):
        rows.append(
            {
                "as_of_utc": f"2026-04-{i:02d}T00:00:00Z",
                "source_id": "label_guided_seed" if i <= 8 else "external_macro_signals",
                "hit": 1 if i <= 9 else 0,
            }
        )
    backtest.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    out = tmp_path / "out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--backtest-json",
            str(backtest),
            "--output-json",
            str(out),
            "--recent-window-sizes",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_symbolic_revalidation_report_v1"
    assert doc.get("overall", {}).get("n_evaluated") == 10
    assert "recent_5" in (doc.get("windows") or {})

