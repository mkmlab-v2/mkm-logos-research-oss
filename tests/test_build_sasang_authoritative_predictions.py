from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_authoritative_predictions as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_build_authoritative_predictions_picks_best_confidence(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    pred_dir = tmp_path / "preds"
    out = tmp_path / "predictions.real.aligned.latest.jsonl"
    report = tmp_path / "alignment_report.json"

    _write_jsonl(
        gt,
        [
            {"sample_id": "S1", "expected_parent": "SY"},
            {"sample_id": "S2", "expected_parent": "SE"},
        ],
    )
    _write_jsonl(
        pred_dir / "predictions.real.latest.jsonl",
        [
            {"sample_id": "S1", "predicted_parent": "SY", "confidence": 0.7},
            {"sample_id": "S2", "predicted_parent": "SE", "confidence": 0.6},
        ],
    )
    _write_jsonl(
        pred_dir / "sasang_predictions_from_btrack_eval_full_mapped_latest.jsonl",
        [
            {"sample_id": "S1", "predicted_parent": "SY", "confidence": 0.9},
            {"sample_id": "NO_MATCH", "predicted_parent": "TE", "confidence": 0.8},
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_authoritative_predictions.py",
            "--gt",
            str(gt),
            "--pred-dir",
            str(pred_dir),
            "--out",
            str(out),
            "--report",
            str(report),
        ],
    )

    assert mod.main() == 0
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    by_id = {r["sample_id"]: r for r in rows}
    assert by_id["S1"]["confidence"] == 0.9
    assert by_id["S2"]["confidence"] == 0.6
