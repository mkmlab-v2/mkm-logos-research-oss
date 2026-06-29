"""Shape check for Saving the News §11 NEWS-EVO-BENCH contract ([HYPO], research_only)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/artifacts/fixtures/news_evo_bench_contract_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/news_evo_bench_contract_v1.schema.json"


def test_news_evo_bench_contract_example_shape() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data.get("schema") == "news_evo_bench_contract_v1"
    assert data.get("hypothesis_tier") == "B"
    for key in (
        "field",
        "dual_rail",
        "lenses",
        "conflict",
        "loss_axes",
        "evolution",
        "final",
        "audit",
        "boundary_ack",
    ):
        assert key in data, f"missing top-level key: {key}"

    field = data["field"]
    assert field.get("regime_id") == "regime_saving_the_news_dual_architecture_hypo"
    assert field.get("personal_rail_id") == "regime_saving_the_news_hyper_personalization"

    common = data["dual_rail"]["common"]
    assert common.get("auto_apply_forbidden") is True
    personal = data["dual_rail"]["personal"]
    assert "intake_ref" in personal

    logos = data["lenses"]["logos"]
    assert logos.get("role") == "NON_GATING"

    loss = data["loss_axes"]
    for axis in ("L_price", "L_general", "L_compression_raw", "L_calibration"):
        assert axis in loss
        assert "eval_ref" in loss[axis]
    assert loss["L_compression_raw"].get("promotion_gate_candidate") == "raw_only"

    evo = data["evolution"]
    assert evo.get("bench_id") == "NEWS-EVO-BENCH"
    assert evo.get("mode") == "suggest_only_offline"
    assert "auto_merge_to_track_a" in evo.get("forbidden", [])

    final = data["final"]
    assert final["decision_label"] in ("WATCH", "HOLD")
    assert final["cms_publish_allowed"] is False

    audit = data["audit"]
    assert audit.get("model_route") == "local_stub_no_llm"
    assert "raw_repair_reporting" in audit


def test_news_evo_bench_contract_schema_file_exists() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("title") == "news_evo_bench_contract_v1"
