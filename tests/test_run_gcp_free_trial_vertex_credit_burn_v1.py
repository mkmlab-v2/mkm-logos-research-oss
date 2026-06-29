"""Dry-run tests for GCP Free Trial Vertex burn script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_gcp_free_trial_vertex_credit_burn_v1.py"


def test_dry_run_asset_rag_writes_jsonl(tmp_path: Path) -> None:
    out_json = tmp_path / "summary.json"
    out_jsonl = tmp_path / "assets.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--calls",
            "3",
            "--prompt-profile",
            "asset_rag",
            "--wave-id",
            "test_wave",
            "--out-json",
            str(out_json),
            "--out-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["prompt_profile"] == "asset_rag"
    assert summary["dry_run"] is True
    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    row = json.loads(lines[0])
    assert row["schema"] == "gcp_free_trial_vertex_burn_row_v1"
    assert row["hypothesis_tier"] == "B"
    assert "[HYPO]" in row["prompt"]
