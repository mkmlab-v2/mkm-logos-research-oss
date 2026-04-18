from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_overlay_view_v1_latest.json"
SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"


def test_overlay_view_artifact_contract() -> None:
    assert ART.is_file(), "run: py scripts/build_btrack_prophecy_score_insight_overlay_view_v1.py"
    data = json.loads(ART.read_text(encoding="utf-8-sig"))
    assert data.get("schema") == "btrack_prophecy_score_insight_overlay_view_v1"
    assert data.get("research_only") is True
    assert isinstance(data.get("version"), str) and data["version"]
    assert isinstance(data.get("paired_score_ref"), str)
    assert isinstance(data.get("insight_sidecar_ref"), str)
    joined = data.get("joined_rows")
    assert isinstance(joined, list) and len(joined) >= 1
    score = json.loads(SCORE.read_text(encoding="utf-8-sig"))
    rows = score.get("rows") if isinstance(score.get("rows"), list) else []
    assert len(joined) == len(rows)
    assert data.get("joined_row_count") == len(joined)
    for i, block in enumerate(joined):
        assert isinstance(block, dict)
        assert isinstance(block.get("score_row"), dict)
        obs = block.get("insight_sidecar_observation")
        assert obs is None or isinstance(obs, dict)
        if isinstance(obs, dict):
            assert obs.get("paired_row_index") in (None, i)
