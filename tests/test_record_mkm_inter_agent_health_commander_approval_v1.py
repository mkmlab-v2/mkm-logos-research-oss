"""Commander approval recorder for B-track health domain relax."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.record_mkm_inter_agent_health_commander_approval_v1 import build


def test_commander_approval_schema(tmp_path: Path, monkeypatch) -> None:
    cand = tmp_path / "candidate.json"
    cand.write_text(
        json.dumps(
            {
                "proposed_variant_id": "health_hangul_relaxed_cap_0.50",
                "proposed_run_config": {
                    "domain_relaxed_max_saving_overrides": {"health": 0.5, "hangul": 0.5}
                },
                "bench_promotion_eligible_without_human": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    import scripts.record_mkm_inter_agent_health_commander_approval_v1 as mod

    monkeypatch.setattr(mod, "CANDIDATE", cand)
    doc = build()
    assert doc["commander_approved"] is True
    assert doc["track_a_bench_promotion_approved"] is False
    assert doc["approval_scope"] == "b_track_inter_agent_v2_routing_only"


def test_b_track_routing_uses_commander_approved_overrides() -> None:
    from scripts.compression_v2_routing_profile_v1 import (
        HEALTH_COMMANDER_APPROVAL,
        routing_profile_kwargs,
    )

    if not HEALTH_COMMANDER_APPROVAL.is_file():
        return
    kw = routing_profile_kwargs("b_track_domain_relax")
    assert kw.get("health_commander_approval_path")
    overrides = kw.get("domain_relaxed_max_saving_overrides") or {}
    assert overrides.get("health") == 0.5
    assert overrides.get("hangul") == 0.5
