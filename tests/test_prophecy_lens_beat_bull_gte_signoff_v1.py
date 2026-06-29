from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_gte_eval_requires_signoff(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    pending = tmp_path / "pending.json"
    pending.write_text(
        json.dumps(
            {
                "approved": False,
                "gate_definition_change_acknowledged": False,
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts/eval_prophecy_promotion_gates_v1.py"),
            "--lens-beat-bull-comparator",
            "gte",
            "--gte-human-signoff-json",
            str(pending),
            "--stdout-only",
            "--output",
            str(tmp_path / "out.json"),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2


def test_signoff_packet_builds(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    out = tmp_path / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts/build_prophecy_lens_beat_bull_gte_signoff_packet_v1.py"),
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_lens_beat_bull_gte_signoff_readiness_v1"
    assert "counterfactual" in doc
