"""June KOSPI 4AI overlay smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"


def _evolution_rules() -> dict:
    if not EVOLUTION_RULES.is_file():
        return {}
    return json.loads(EVOLUTION_RULES.read_text(encoding="utf-8"))


def _lens3_heavy_applied() -> bool:
    rules = _evolution_rules()
    if rules.get("last_candidate_apply_id") != "v2_lens3_heavy":
        return False
    w = rules.get("blend_weights_v2") or {}
    return float(w.get("session_myeongni", 0)) >= 0.29


def _v2_calendar_lock_enabled() -> bool:
    pol = _evolution_rules().get("four_ai_coordinator_policy") or {}
    return bool(pol.get("lock_coordinator_to_v2_calendar"))


def test_build_4ai_report_from_calendar() -> None:
    import scripts.kospi_june_4ai_prophecy_overlay_v1 as mod

    cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file():
        cal = {
            "year_month": "2026-06",
            "multilens_profile": "v2_multilens",
            "rows": [
                {
                    "session_date": "2026-06-01",
                    "weekday_ko": "월",
                    "predicted_direction": "neutral",
                    "pillars_session": {},
                    "kospi_index_prophecy": {"predicted_close_mid": 8475},
                    "blend": {
                        "channels": [
                            {"channel": "momentum_overlay", "direction": "bull", "weight": 0.12},
                            {"channel": "field_regime", "direction": "bear", "weight": 0.12},
                            {"channel": "session_myeongni", "direction": "neutral", "weight": 0.22},
                            {"channel": "sasang", "direction": "bull", "weight": 0.12},
                        ]
                    },
                }
            ],
        }
    else:
        cal = mod._read_json(cal_path)

    doc = mod.build_4ai_report(cal)
    assert doc["schema"] == "kospi_june_4ai_prophecy_report_v1"
    assert doc["hypothesis_tier"] == "B"
    assert len(doc["rows"]) >= 1
    row0 = doc["rows"][0]
    assert len(row0["four_ai_agents"]) == 4
    assert "absolute_balance" in row0
    assert row0["four_ai_direction"] in ("bull", "bear", "neutral")
    assert "channel_consensus" in row0["absolute_balance"]


def test_4ai_aligns_with_v2_on_calendar() -> None:
    import scripts.kospi_june_4ai_prophecy_overlay_v1 as mod

    cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file():
        return
    cal = mod._read_json(cal_path)
    policy = mod._load_blend_policy(ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json")
    doc = mod.build_4ai_report(cal, blend_policy=policy)
    rows = doc["rows"]
    assert rows
    aligned = sum(1 for r in rows if r.get("v2_aligned"))
    if _v2_calendar_lock_enabled():
        assert aligned == len(rows), f"4AI misaligned on {len(rows) - aligned} days (v2 lock)"
    elif _lens3_heavy_applied():
        assert aligned >= len(rows) // 2, f"4AI misaligned on {len(rows) - aligned} days (lens3_heavy)"
    else:
        assert aligned == len(rows), f"4AI misaligned on {len(rows) - aligned} days"


def test_weighted_agree_or_anchor_on_bull_bear_split() -> None:
    import scripts.kospi_june_4ai_prophecy_overlay_v1 as mod

    policy = mod._load_blend_policy(ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json")
    channels = [
        {"channel": "session_myeongni", "direction": "bull", "weight": 0.22},
        {"channel": "myeongni_independent", "direction": "neutral", "weight": 0.14},
        {"channel": "sasang", "direction": "bull", "weight": 0.12},
        {"channel": "macro", "direction": "neutral", "weight": 0.1},
        {"channel": "logos_non_gating", "direction": "bear", "weight": 0.08},
        {"channel": "field_regime", "direction": "bear", "weight": 0.12},
        {"channel": "momentum_overlay", "direction": "bear", "weight": 0.12},
        {"channel": "ensemble_kospi_causal", "direction": "bear", "weight": 0.1},
    ]
    agents = [mod._agent_vote_from_channels(channels, aid) for aid in mod.FOUR_AI]
    coord = mod._coordinator(agents, channels=channels, blend_policy=policy)
    assert coord["coordinator_direction"] == "bear"
    assert coord["resolution_mode"] in ("four_ai_channel_anchor", "four_ai_weighted_agree")
    assert coord["aligned_with_v2_channel"] is True


def test_coordinator_kpi_on_report() -> None:
    import scripts.kospi_june_4ai_prophecy_overlay_v1 as mod

    cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file():
        return
    cal = mod._read_json(cal_path)
    policy = mod._load_blend_policy(ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json")
    doc = mod.build_4ai_report(cal, blend_policy=policy)
    kpi = doc.get("coordinator_kpi")
    assert isinstance(kpi, dict)
    rate = float(kpi.get("v2_alignment_rate", 0))
    if _v2_calendar_lock_enabled():
        assert rate == 1.0
    elif _lens3_heavy_applied():
        assert rate >= 0.5
    else:
        assert rate == 1.0
    assert kpi.get("autonomous_consensus_rate", 0) >= 0.2
