from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_nextday_observation_report_v1(tmp_path: Path):
    go = tmp_path / "go.json"
    freeze = tmp_path / "freeze.json"
    rehearse = tmp_path / "rehearse.json"
    drift = tmp_path / "drift.json"
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    hist = tmp_path / "history.jsonl"
    go.write_text(json.dumps({"verdict": "go"}), encoding="utf-8")
    freeze.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    rehearse.write_text(json.dumps({"ops_alert_summary": {"ops_alert": False}}), encoding="utf-8")
    drift.write_text(json.dumps({"status": "stable"}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_nextday_observation_report_v1.py",
        "--go-no-go-json",
        str(go),
        "--freeze-v2-stability-gate-json",
        str(freeze),
        "--rehearsal-latest-json",
        str(rehearse),
        "--strict-freeze-drift-gate-json",
        str(drift),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
        "--history-jsonl",
        str(hist),
        "--append-history",
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_nextday_observation_report_v1"
    assert data["verdict"] == "pass"
    lines = [x for x in hist.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
    assert out_md.exists()

