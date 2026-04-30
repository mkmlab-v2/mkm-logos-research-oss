from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "extract_layer5_incident_candidates_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_extract_candidates_from_keywords(tmp_path: Path) -> None:
    inp = tmp_path / "ops.jsonl"
    out = tmp_path / "cand.jsonl"
    summary = tmp_path / "sum.json"
    _write_jsonl(
        inp,
        [
            {"status": "PASS"},
            {"high_reliability_decision": "HOLD"},
            {"note": "track b direct_bridge to track a"},
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--input-jsonl",
            str(inp),
            "--output-jsonl",
            str(out),
            "--summary-json",
            str(summary),
            "--max-cases",
            "10",
            "--control-ratio",
            "0.5",
            "--seed",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) >= 2
    assert all("review_status" in r and r["review_status"] == "draft" for r in rows)
    assert any(r["expected_block"] for r in rows)
    assert any(not r["expected_block"] for r in rows)
    s = json.loads(summary.read_text(encoding="utf-8"))
    assert s["schema"] == "layer5_incident_candidates_summary_v1"
