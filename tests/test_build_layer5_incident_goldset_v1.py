from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_layer5_incident_goldset_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_goldset_balanced_sampling(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    out = tmp_path / "goldset.jsonl"
    summary = tmp_path / "summary.json"
    _write_jsonl(
        source,
        [
            {"high_reliability_decision": "HOLD"},
            {"high_reliability_decision": "PASS"},
            {"promotion_gate": "fail"},
            {"promotion_gate": "pass"},
            {"lock_state": "locked"},
            {"lock_state": "unlocked"},
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--input-jsonl",
            str(source),
            "--output-jsonl",
            str(out),
            "--summary-json",
            str(summary),
            "--sample-size",
            "4",
            "--seed",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 4
    assert all("expected_block" in row for row in lines)
    s = json.loads(summary.read_text(encoding="utf-8"))
    assert s["schema"] == "layer5_incident_goldset_summary_v1"
    assert s["sample_size_written"] == 4
