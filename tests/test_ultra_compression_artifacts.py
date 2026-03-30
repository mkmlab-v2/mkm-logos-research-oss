# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ultra compression benchmark artifacts and decision gate.
# Keywords: multilens, ultra-compression, benchmark, gate

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_BASELINE_LOCK = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_BASELINE_LOCK_V1.json"
_ROUND1 = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ROUND1_V1.json"
_ROUND2 = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ROUND2_V1.json"
_DECISION = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
_ACTIVE = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_ultra_baseline_lock_contract() -> None:
    d = _load(_BASELINE_LOCK)
    assert d.get("schema") == "multilens_ultra_compression_baseline_lock_v1"
    assert 0.0 <= float(d.get("baseline_global_token_saving_rate", -1.0)) <= 1.0
    assert float(d.get("targets", {}).get("saving_target", -1.0)) == 0.50


def test_ultra_round_contracts() -> None:
    r1 = _load(_ROUND1)
    r2 = _load(_ROUND2)
    assert r1.get("schema") == "multilens_ultra_compression_round1_v1"
    assert int(r1.get("candidate_count", 0)) >= 9
    assert len(r1.get("pareto_top2", [])) == 2
    assert r2.get("schema") == "multilens_ultra_compression_round2_v1"
    assert isinstance(r2.get("candidates"), list)
    assert r2.get("selected_candidate") is not None


def test_ultra_decision_contract() -> None:
    d = _load(_DECISION)
    assert d.get("schema") == "multilens_ultra_compression_decision_v1"
    assert d.get("go_no_go") in {"GO", "NO_GO"}
    assert d.get("rollout_policy") in {"global_default", "domain_variable_cap"}


def test_active_report_matches_decision_profile_and_gate() -> None:
    d = _load(_DECISION)
    a = _load(_ACTIVE)
    selected = d.get("selected_candidate", {})
    run_cfg = a.get("run_config", {})
    active_profile = a.get("active_profile", {})
    q = a.get("quality_gate", {})

    assert run_cfg.get("strategy") == selected.get("strategy")
    assert run_cfg.get("intensity") == selected.get("intensity")
    assert float(run_cfg.get("general_max_saving_rate")) == float(selected.get("general_max_saving_rate"))
    assert float(run_cfg.get("sensitive_max_saving_rate")) == float(selected.get("sensitive_max_saving_rate"))
    assert active_profile.get("strategy") == selected.get("strategy")
    assert active_profile.get("intensity") == selected.get("intensity")

    assert abs(float(q.get("jaccard_drop_pp")) - float(selected.get("jaccard_drop_pp"))) < 1e-9
    assert bool(q.get("jaccard_guardrail_ok")) is True
