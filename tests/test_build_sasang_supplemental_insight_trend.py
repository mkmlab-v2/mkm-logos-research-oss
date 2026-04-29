from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_supplemental_insight_trend as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_trend_from_current_and_previous_score(tmp_path: Path, monkeypatch) -> None:
    score = tmp_path / "score.json"
    prev = tmp_path / "prev_trend.json"
    out = tmp_path / "trend.json"

    _write(score, {"supplemental_score": {"value": 0.96}})
    _write(prev, {"current_value": 0.88})

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_supplemental_insight_trend.py",
            "--score",
            str(score),
            "--prev-trend",
            str(prev),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["non_gating_policy"] is True
    assert doc["trend_status"] == "UP"
    assert doc["alert"] is False
    assert float(doc["delta"]) > 0.0
