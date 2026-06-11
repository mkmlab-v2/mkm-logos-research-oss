"""Tests for contributor promotion candidate builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_compression_contributor_promotion_candidate_v1.py"


def test_build_candidate_from_fixtures(tmp_path: Path) -> None:
    validate = tmp_path / "validate.json"
    validate.write_text(
        json.dumps(
            {
                "validation_ok": True,
                "row_count": 12,
                "input_jsonl": "data/compression/examples/x.jsonl",
                "input_sha256": "abc",
            }
        ),
        encoding="utf-8",
    )
    poc = tmp_path / "poc.json"
    poc.write_text(
        json.dumps(
            {
                "case_count": 12,
                "cases_passed": 8,
                "parse_or_api_failures": 0,
                "aggregate": {
                    "mean_jaccard_proxy": 0.72,
                    "mean_token_saving_rate_proxy": 0.15,
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "candidate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--validate-json",
            str(validate),
            "--poc-json",
            str(poc),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["auto_track_a_promotion_allowed"] is False
    assert doc["commander_may_apply_track_a_bridge"] is True
    assert doc["promotion_ladder_step"] == "candidate_only"


def test_build_candidate_fails_low_jaccard(tmp_path: Path) -> None:
    validate = tmp_path / "validate.json"
    validate.write_text(json.dumps({"validation_ok": True, "row_count": 12}), encoding="utf-8")
    poc = tmp_path / "poc.json"
    poc.write_text(
        json.dumps(
            {
                "case_count": 12,
                "cases_passed": 2,
                "aggregate": {"mean_jaccard_proxy": 0.3, "mean_token_saving_rate_proxy": 0.0},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "candidate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--validate-json",
            str(validate),
            "--poc-json",
            str(poc),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["commander_may_apply_track_a_bridge"] is False
