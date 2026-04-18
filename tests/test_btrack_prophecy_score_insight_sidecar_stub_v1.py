from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"


def test_sidecar_stub_artifact_contract() -> None:
    assert ART.is_file(), "run: py scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
    data = json.loads(ART.read_text(encoding="utf-8-sig"))
    assert data.get("schema") == "btrack_prophecy_score_insight_sidecar_v1"
    assert data.get("research_only") is True
    assert data.get("experimental_attribution_enabled") is False
    assert isinstance(data.get("paired_score_ref"), str) and data["paired_score_ref"]
    assert isinstance(data.get("feature_contract_v1"), list)
    assert data.get("version") == "1.1.0"

    score = json.loads(SCORE.read_text(encoding="utf-8-sig"))
    rows = score.get("rows") if isinstance(score.get("rows"), list) else []
    pdf = data.get("per_date_features")
    assert isinstance(pdf, list)
    assert len(pdf) == len(rows)
    for i, row in enumerate(pdf):
        assert row.get("observation_only") is True
        assert row.get("paired_row_index") == i
        snap = row.get("lens_scores_snapshot")
        assert isinstance(snap, dict)
        for k in ("logos", "myeongni", "sasang"):
            assert k in snap
