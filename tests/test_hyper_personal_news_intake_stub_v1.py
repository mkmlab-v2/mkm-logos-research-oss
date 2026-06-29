"""Shape check for Saving the News §10 hyper-personal intake stub ([HYPO], research_only)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/artifacts/fixtures/hyper_personal_news_intake_stub_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/hyper_personal_news_intake_stub_v1.schema.json"


def test_hyper_personal_news_intake_stub_example_json_shape() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data.get("schema") == "hyper_personal_news_intake_stub_v1"
    assert data.get("hypothesis_tier") == "B"
    for key in ("field", "lenses", "conflict", "final", "audit", "boundary_ack"):
        assert key in data, f"missing top-level key: {key}"

    field = data["field"]
    assert field.get("regime_id") == "regime_saving_the_news_hyper_personalization"
    priors = field["priors"]
    assert 0 <= priors["sasang_scalar"] <= 1
    assert -0.5 <= priors["myeongni_day_pillar_prior_hypo"] <= 0.5
    assert priors["wellness_hypo_budget"] == 0.25

    logos = data["lenses"]["logos"]
    assert logos.get("role") == "NON_GATING"

    final = data["final"]
    assert final["decision_label"] in ("WATCH", "HOLD")
    assert final["cms_publish_allowed"] is False

    audit = data["audit"]
    assert audit.get("model_route") == "local_stub_no_llm"
    assert "weights" in audit
    assert audit.get("bench_axes", {}).get("news_hp_rt") == "NOT_MEASURED"


def test_hyper_personal_news_intake_stub_schema_file_exists() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("title") == "hyper_personal_news_intake_stub_v1"
