"""Pack 0-B pillars engine crosscheck."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_myeongri_pillars_engine_crosscheck_v1 import _classify, _saju_tuple
from scripts.myeongri_deterministic_lora_golden_views_v1 import pillars_view


def test_classify_mode_collapse() -> None:
    gold_p = pillars_view(
        {
            "schema": "saju_global_birth_result_v1",
            "version": "1.0.0",
            "resolution": {},
            "full_saju": {"saju": {"year": "갑자", "month": "을축", "day": "병인", "hour": "정묘"}},
        }
    )
    engine_p = dict(gold_p)
    pred_p = pillars_view(
        {
            "schema": "saju_global_birth_result_v1",
            "version": "1.0.0",
            "resolution": {},
            "full_saju": {"saju": {"year": "계묘", "month": "임자", "day": "신사", "hour": "기미"}},
        }
    )
    assert _classify(gold_p=gold_p, engine_p=engine_p, pred_p=pred_p) == "model_mode_collapse_while_golden_ok"


def test_crosscheck_report_schema(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    golden = root / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
    if not golden.is_file():
        return
    out = tmp_path / "crosscheck.json"
    import subprocess
    import sys

    rc = subprocess.call(
        [
            sys.executable,
            str(root / "scripts/build_myeongri_pillars_engine_crosscheck_v1.py"),
            "--golden-jsonl",
            str(golden),
            "--predictions-jsonl",
            str(root / "reports/myeongri_deterministic_lora_locked_eval_predictions_latest.jsonl"),
            "--out-json",
            str(out),
            "--sample-limit",
            "3",
            "--all-locked-eval",
        ],
        cwd=str(root),
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongri_pillars_engine_crosscheck_v1"
    assert doc["rows_analyzed"] == 3
    assert _saju_tuple(pillars_view({})) is None
