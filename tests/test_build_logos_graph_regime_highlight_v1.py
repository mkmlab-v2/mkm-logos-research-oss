from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_graph_regime_highlight_v1.py"


def test_regime_highlight_non_gating(tmp_path: Path) -> None:
    regime = tmp_path / "regime.json"
    regime.write_text(
        json.dumps(
            {
                "regimes": {
                    "sideways_accumulation": {"fingerprint": {}},
                    "bull_pump": {"fingerprint": {}},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    nodes = tmp_path / "nodes.jsonl"
    rows = [
        {
            "node_id": "aramaic::Gen.1.1",
            "ref": "Gen.1.1",
            "regime_tags": ["sideways_accumulation"],
        },
        {
            "node_id": "regime::sideways_accumulation",
            "kind": "regime",
            "label": "sideways",
        },
    ]
    with nodes.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    out = tmp_path / "highlight.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--regime-map-json",
            str(regime),
            "--nodes-jsonl",
            str(nodes),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_graph_regime_highlight_v1"
    assert doc["no_trading_trigger"] is True
    assert doc["gating_status"] == "NON_GATING"
    assert doc["highlight_counts_by_regime"]["sideways_accumulation"] == 1
