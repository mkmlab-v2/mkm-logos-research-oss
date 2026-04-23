from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_insight_slice_stability_v1(tmp_path: Path):
    hist = tmp_path / "hist.jsonl"
    out = tmp_path / "slice.json"
    e1 = {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "insights": [{"row_id": "Gen.1.1"}, {"row_id": "Gen.1.2"}],
    }
    e2 = {
        "generated_at_utc": "2026-01-02T00:00:00Z",
        "insights": [{"row_id": "Gen.1.1"}, {"row_id": "Exod.1.1"}],
    }
    hist.write_text(json.dumps(e1, ensure_ascii=False) + "\n" + json.dumps(e2, ensure_ascii=False) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_insight_slice_stability_v1.py",
        "--history-jsonl",
        str(hist),
        "--window",
        "2",
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_insight_slice_stability_v1"
    assert data["counts"]["slice_change_count"] >= 1

