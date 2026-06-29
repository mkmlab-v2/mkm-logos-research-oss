"""pytest: paste chart ledger bridge smoke (tsx subprocess)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects/no1kmedi"


def test_paste_chart_ledger_bridge_smoke() -> None:
    proc = subprocess.run(
        ["npx", "--yes", "tsx", "./scripts/smoke-clinician-paste-chart-ledger-bridge-v1.ts"],
        cwd=str(NO1K),
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-1200:] if proc.stderr else proc.stdout
    lines = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    assert lines, "empty stdout"
    report = json.loads(lines[-1])
    assert report.get("ok") is True
    assert report.get("schema") == "smoke_clinician_paste_chart_ledger_bridge_v1"
