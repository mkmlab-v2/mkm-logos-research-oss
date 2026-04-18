from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"


def test_sidecar_stub_artifact_contract() -> None:
    assert ART.is_file(), "run: py scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
    data = json.loads(ART.read_text(encoding="utf-8-sig"))
    assert data.get("schema") == "btrack_prophecy_score_insight_sidecar_v1"
    assert data.get("research_only") is True
    assert data.get("experimental_attribution_enabled") is False
    assert isinstance(data.get("paired_score_ref"), str) and data["paired_score_ref"]
    assert data.get("per_date_features") is None
    assert isinstance(data.get("feature_contract_v1"), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
