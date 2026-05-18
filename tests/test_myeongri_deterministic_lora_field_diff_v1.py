from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.myeongri_deterministic_lora_golden_views_v1 import (
    aggregate_field_diffs,
    build_field_diff_v1,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
SCRIPT = ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"


def _golden_row() -> dict:
    line = FIXTURE.read_text(encoding="utf-8").splitlines()[0]
    return json.loads(line)


def test_field_diff_all_match_on_golden_copy() -> None:
    row = _golden_row()
    exp = row["expected_result"]
    diff = build_field_diff_v1(exp, exp)
    assert diff["four_pillars_match_rate"] == 1.0
    assert diff["local_iso"]["match"] is True
    assert diff["daewoon"]["len_match"] is True


def test_field_diff_detects_pillar_and_local_iso_mismatch() -> None:
    row = _golden_row()
    exp = row["expected_result"]
    pred = json.loads(json.dumps(exp))
    pred["full_saju"]["saju"]["year"] = "틀림"
    pred["resolution"]["local_iso"] = "1999-01-01T00:00:00+00:00"
    diff = build_field_diff_v1(exp, pred)
    assert diff["four_pillars"]["year"]["match"] is False
    assert diff["local_iso"]["match"] is False
    assert diff["four_pillars_match_rate"] == 0.75


def test_oracle_eval_includes_field_diff_aggregate(tmp_path: Path) -> None:
    report = tmp_path / "eval.json"
    preds = tmp_path / "preds.jsonl"
    subprocess.check_call(
        [
            sys.executable,
            str(SCRIPT),
            "--golden-jsonl",
            str(FIXTURE),
            "--oracle-golden",
            "--predictions-jsonl",
            str(preds),
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
    )
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["field_diff_aggregate"]["rows"] == 2
    assert doc["field_diff_aggregate"]["four_pillars_all_match_rate"] == 1.0
    assert "field_diff" in doc["per_row"][0]


def test_aggregate_field_diffs_empty() -> None:
    assert aggregate_field_diffs([])["rows"] == 0
