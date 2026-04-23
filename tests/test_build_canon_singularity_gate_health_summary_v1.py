from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_gate_health_summary_v1(tmp_path: Path):
    history = tmp_path / "history.jsonl"
    out = tmp_path / "health.json"
    history.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "original_corpus_regime_singularity_canon_quality_gate_event_v1",
                        "generated_at_utc": "2026-04-23T01:00:00Z",
                        "result": "pass",
                        "error": None,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "schema": "original_corpus_regime_singularity_canon_quality_gate_event_v1",
                        "generated_at_utc": "2026-04-23T02:00:00Z",
                        "result": "fail",
                        "error": "x",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_gate_health_summary_v1.py",
        "--history-jsonl",
        str(history),
        "--window",
        "2",
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_quality_gate_health_summary_v1"
    assert data["counts"]["pass_count"] == 1
    assert data["counts"]["fail_count"] == 1
    assert data["latest_status"]["result"] == "fail"
    assert data["last_failure"]["error"] == "x"

