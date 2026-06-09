"""Drill simulation: rebuild index + overlay gate path ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/multi_res_trades_smoke_v1.json"


def test_drift_recovery_rebuild_chain(tmp_path: Path) -> None:
    index_out = tmp_path / "fills_index.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/multi_res_fills_join_v1.py",
            "--trades-json",
            str(FIXTURE),
            "--out",
            str(index_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(index_out.read_text(encoding="utf-8"))
    assert doc["meta"]["n_fill_rows"] == 3

    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_ops_memory_index_lib_v1 import build_fills_overlay_nodes

    nodes = build_fills_overlay_nodes(ROOT)
    # Uses live reports/multi_res_fills_index if present; drill validates API exists
    assert isinstance(nodes, dict)
