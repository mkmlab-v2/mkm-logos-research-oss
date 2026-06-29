"""Gate-driven lens maturity v2 axis scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lens_maturity_scoring_v2 import (  # noqa: E402
    score_logos_d_v2,
    score_myeongni_d_v2,
    score_sasang_b_c_v2,
    score_sasang_d_v2,
)


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def test_myeongni_d_from_observation_report(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "myeongni_lens_observation_report_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "myeongni_lens_observation_report_v1",
                "separation_contract_ok": True,
                "not_hit_rate_proof": True,
                "gates": {"stage2_realset_pass": True, "promotion_status": "PASS"},
                "snapshots": {"market_direction_score": 0.0},
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    d, notes = score_myeongni_d_v2(tmp_path, _read)
    assert d >= 7.5
    assert "separation_contract_ok" in notes


def test_myeongni_d_shadow_hit_bonus(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "myeongni_lens_observation_report_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "myeongni_lens_observation_report_v1",
                "separation_contract_ok": True,
                "not_hit_rate_proof": True,
                "gates": {"stage2_realset_pass": True, "promotion_status": "PASS"},
                "snapshots": {"market_direction_score": 0.0},
                "shadow_price_hits": {
                    "myeongni": {
                        "instrument": "btc",
                        "price_directional_hit_rate": 0.6,
                        "n_evaluated": 30,
                    }
                },
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    d, notes = score_myeongni_d_v2(tmp_path, _read)
    assert d >= 8.0
    assert any("myeongni_shadow_hit=0.600" in n for n in notes)


def test_logos_d_hit_tiers(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "prophecy_logos_revalidation_oos_gate_latest.json").write_text(
        json.dumps(
            {
                "gate": {"go": True, "checks": {"oos_sharpe_pass": True}},
                "oos_metrics": {"directional_hit_rate_active": 0.54},
            }
        ),
        encoding="utf-8",
    )
    d, _ = score_logos_d_v2(tmp_path, _read)
    assert 7.0 <= d <= 8.0


def test_sasang_bc_fusion_pass(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "sasang_4agent_fusion_gate_latest.json").write_text(
        json.dumps({"decision": "FUSION_GATE_PASS"}), encoding="utf-8"
    )
    (art / "sasang12_promotion_candidate_gate_latest.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    (art / "sasang_4agent_promotion_gate_latest.json").write_text(
        json.dumps({"decision": "GO", "checks": {"fusion_gate_pass": True}}),
        encoding="utf-8",
    )
    (art / "sasang_high_reliability_gate_latest.json").write_text(
        json.dumps({"decision": "PASS"}), encoding="utf-8"
    )
    (art / "sasang_independent_lens_latest.json").write_text(
        json.dumps(
            {"sasang_stream_outputs": {"machine_readables": {"heat_proxy": 0.6}}}
        ),
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "sasang_rule_based_response_v1_latest.md").write_text("# ok\n", encoding="utf-8")
    b, c, notes = score_sasang_b_c_v2(tmp_path, _read)
    assert b >= 7.5
    assert c >= 7.0
    assert "fusion_gate_PASS" in notes


def test_sasang_d_observation_and_shadow_hit(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "sasang_high_reliability_gate_latest.json").write_text(
        json.dumps(
            {
                "decision": "PASS",
                "snapshot": {"recall_macro": 0.7, "brier_score": 0.16},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "sasang_lens_observation_report_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "sasang_lens_observation_report_v1",
                "separation_contract_ok": True,
                "not_hit_rate_proof": True,
                "shadow_price_hit": {
                    "price_directional_hit_rate": 0.6,
                    "n_evaluated": 30,
                },
            }
        ),
        encoding="utf-8",
    )
    d, notes = score_sasang_d_v2(tmp_path, _read)
    assert d >= 7.5
    assert "shadow_hit=0.600" in " ".join(notes)
