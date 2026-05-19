from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.myeongri_deterministic_lora_golden_views_v1 import (
    PILLARS_ONLY_SCHEMA,
    four_pillars_match,
    pillars_only_supervision_v1,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
BUILD = ROOT / "scripts" / "build_myeongri_pillars_only_sft_v1.py"
EVAL = ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"


def test_pillars_only_supervision_from_golden() -> None:
    row = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    sup = pillars_only_supervision_v1(row["expected_result"])
    assert sup["schema"] == PILLARS_ONLY_SCHEMA
    assert sup["saju"]["year"] == "임신"


def test_four_pillars_match_accepts_pillars_only_schema() -> None:
    row = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    exp = row["expected_result"]
    pred = pillars_only_supervision_v1(exp)
    assert four_pillars_match(exp, pred)


def test_build_pillars_only_sft_smoke(tmp_path: Path) -> None:
    out = tmp_path / "pillars_sft.jsonl"
    subprocess.check_call(
        [
            sys.executable,
            str(BUILD),
            "--input-jsonl",
            str(FIXTURE),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
    )
    lines = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    target = json.loads(lines[0]["output"])
    assert target["schema"] == PILLARS_ONLY_SCHEMA
    assert "daewoon" not in lines[0]["output"]
    assert "myeongri_pillars_only" in lines[0]["instruction"]


def test_oracle_pillars_only_curriculum_eval(tmp_path: Path) -> None:
    report = tmp_path / "eval.json"
    preds = tmp_path / "preds.jsonl"
    subprocess.check_call(
        [
            sys.executable,
            str(EVAL),
            "--golden-jsonl",
            str(FIXTURE),
            "--oracle-golden",
            "--pillars-only-curriculum",
            "--predictions-jsonl",
            str(preds),
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
    )
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["alignment_tier"] == "pillars_only"
    assert doc["alignment_pass_rate"] == 1.0
    assert doc["pillars_only_curriculum"] is True
