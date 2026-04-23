from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_observation_streak_report_v1(tmp_path: Path):
    hist = tmp_path / "history.jsonl"
    out_json = tmp_path / "streak.json"
    out_md = tmp_path / "streak.md"
    rows = [
        {"verdict": "pass", "hold_reasons": []},
        {"verdict": "pass", "hold_reasons": []},
        {"verdict": "pass", "hold_reasons": []},
    ]
    hist.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_observation_streak_report_v1.py",
        "--history-jsonl",
        str(hist),
        "--window",
        "3",
        "--min-pass-count",
        "3",
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_observation_streak_report_v1"
    assert data["verdict"] == "pass"
    assert data["metrics"]["pass_count"] == 3
    assert out_md.exists()

