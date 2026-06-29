from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_btc_shadow_requires_signoff(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    pending = tmp_path / "pending.json"
    pending.write_text(
        json.dumps(
            {
                "approved": False,
                "instrument_layer_change_acknowledged": False,
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts/build_btrack_btc_margin_wf_research_shadow_v1.py"),
            "--signoff-json",
            str(pending),
            "--output",
            str(tmp_path / "out.json"),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2


def test_btc_signoff_packet_builds(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    out = tmp_path / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts/build_btrack_btc_margin_wf_signoff_packet_v1.py"),
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_btc_margin_wf_signoff_readiness_v1"
    assert "margin_oos" in doc
