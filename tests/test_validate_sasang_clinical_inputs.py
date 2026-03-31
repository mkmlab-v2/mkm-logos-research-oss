from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_sasang_clinical_inputs as v


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_validate_inputs_success(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    pred = tmp_path / "pred.jsonl"
    _write_jsonl(gt, [{"sample_id": "R1", "expected_parent": "TY"}])
    _write_jsonl(pred, [{"sample_id": "R1", "predicted_parent": "TY", "confidence": 0.9}])

    monkeypatch.setattr("sys.argv", ["validate_sasang_clinical_inputs.py", "--gt", str(gt), "--pred", str(pred)])
    assert v.main() == 0

