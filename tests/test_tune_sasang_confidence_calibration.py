from __future__ import annotations

import json
from pathlib import Path

from scripts import tune_sasang_confidence_calibration as mod


def test_tune_confidence_affine_rewrites_values(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "in.jsonl"
    dst = tmp_path / "out.jsonl"
    src.write_text(
        "\n".join(
            [
                json.dumps({"sample_id": "a", "predicted_parent": "SY", "confidence": 0.70}),
                json.dumps({"sample_id": "b", "predicted_parent": "TE", "confidence": 0.85}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "tune_sasang_confidence_calibration.py",
            "--input-jsonl",
            str(src),
            "--output-jsonl",
            str(dst),
            "--scale",
            "0.2",
            "--offset",
            "0.8",
        ],
    )

    assert mod.main() == 0
    rows = [json.loads(x) for x in dst.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    assert rows[0]["confidence"] > 0.9
    assert rows[1]["confidence"] > rows[0]["confidence"]
    assert rows[0]["calibration_tag"] == "sasang_confidence_affine_v1"
