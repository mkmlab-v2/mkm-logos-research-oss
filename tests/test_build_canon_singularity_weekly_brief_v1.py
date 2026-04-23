from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_weekly_brief_v1(tmp_path: Path):
    insight_hist = tmp_path / "insight.jsonl"
    gate_hist = tmp_path / "gate.jsonl"
    health = tmp_path / "health.json"
    slice_json = tmp_path / "slice.json"
    out_json = tmp_path / "weekly.json"
    out_md = tmp_path / "weekly.md"

    insight_hist.write_text(
        json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z", "insights": [{"row_id": "Gen.1.1", "best_regime": "bull", "score": 0.5}], "meta": {"dominant_regime_in_top_n": "bull"}})
        + "\n"
        + json.dumps({"generated_at_utc": "2026-01-02T00:00:00Z", "insights": [{"row_id": "Gen.1.2", "best_regime": "bull", "score": 0.6}], "meta": {"dominant_regime_in_top_n": "bull"}})
        + "\n",
        encoding="utf-8",
    )
    gate_hist.write_text(
        json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z", "result": "pass"}) + "\n" + json.dumps({"generated_at_utc": "2026-01-02T00:00:00Z", "result": "pass"}) + "\n",
        encoding="utf-8",
    )
    health.write_text(json.dumps({"health_level": "green"}, ensure_ascii=False), encoding="utf-8")
    slice_json.write_text(json.dumps({"counts": {"slice_change_count": 1}}, ensure_ascii=False), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_weekly_brief_v1.py",
        "--insight-history-jsonl",
        str(insight_hist),
        "--gate-history-jsonl",
        str(gate_hist),
        "--health-summary-json",
        str(health),
        "--slice-stability-json",
        str(slice_json),
        "--window",
        "7",
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_weekly_brief_v1"
    assert out_md.exists()

