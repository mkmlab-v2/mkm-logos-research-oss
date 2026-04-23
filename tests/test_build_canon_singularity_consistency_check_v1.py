from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_consistency_check_v1(tmp_path: Path):
    gate_hist = tmp_path / "gate.jsonl"
    insight_hist = tmp_path / "insight.jsonl"
    health = tmp_path / "health_policy.json"
    insight_gate = tmp_path / "insight_gate.json"
    delta = tmp_path / "delta.json"
    out = tmp_path / "out.json"

    gate_hist.write_text(
        "\n".join(
            [
                json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z", "result": "pass"}),
                json.dumps({"generated_at_utc": "2026-01-02T00:00:00Z", "result": "pass"}),
                json.dumps({"generated_at_utc": "2026-01-03T00:00:00Z", "result": "pass"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    insight_hist.write_text(
        "\n".join(
            [
                json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z", "counts": {"insight_rows": 12}}),
                json.dumps({"generated_at_utc": "2026-01-02T00:00:00Z", "counts": {"insight_rows": 12}}),
                json.dumps({"generated_at_utc": "2026-01-03T00:00:00Z", "counts": {"insight_rows": 12}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    health.write_text(json.dumps({"status": "pass"}, ensure_ascii=False), encoding="utf-8")
    insight_gate.write_text(json.dumps({"status": "pass"}, ensure_ascii=False), encoding="utf-8")
    delta.write_text(
        json.dumps({"counts": {"added_count": 0, "removed_count": 0, "changed_count": 0}}, ensure_ascii=False),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_consistency_check_v1.py",
        "--gate-history-jsonl",
        str(gate_hist),
        "--insight-history-jsonl",
        str(insight_hist),
        "--health-policy-json",
        str(health),
        "--insight-gate-json",
        str(insight_gate),
        "--insight-delta-json",
        str(delta),
        "--window",
        "3",
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_operational_consistency_check_v1"
    assert data["status"] == "pass"

