# -*- coding: utf-8 -*-
import json
from pathlib import Path

import pytest

from scripts.validate_showroom_public_bundle import validate_bundle


def test_validate_good_bundle(tmp_path: Path) -> None:
    p = tmp_path / "showroom_public_bundle_v1.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {},
        "public_ui": {
            "schema": "showroom_public_ui_v1",
            "direction_abstract": "flat",
            "direction_source": "c2",
            "c2_lamp": "GREEN",
            "ops_fusion_ok": True,
            "return_pct_vs_baseline": None,
            "has_return_pct": False,
            "unrealized_pnl_pct_of_equity": None,
            "has_unrealized_pct": False,
            "baseline_mode": "none",
            "unified_score_balanced": 0.4,
        },
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "C2=GREEN_HOLD · exploratory monitor · no investment advice.",
            "schema_version": "public-event.v1",
            "event_id": "showroom-test-001",
            "source": "ops_showroom_bundle_v1",
            "system_status": "online",
            "active_strategies_count": 1,
            "delayed_metrics": {"delay_seconds": 180, "as_of_utc": "2026-04-03T11:57:00+00:00"},
            "direction_abstract": "flat",
            "disclaimer_ref": "jemaai_showroom_v1",
            "last_ok_utc": "2026-04-03T12:00:00+00:00",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_accepts_logos_delayed_metrics(tmp_path: Path) -> None:
    p = tmp_path / "with_logos.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {},
        "public_ui": {
            "schema": "showroom_public_ui_v1",
            "direction_abstract": "flat",
            "direction_source": "c2",
            "c2_lamp": "GREEN",
            "ops_fusion_ok": True,
            "return_pct_vs_start": None,
            "has_return_pct": False,
            "unrealized_pnl_pct_of_equity": None,
            "has_unrealized_pct": False,
            "baseline_mode": "none",
            "unified_score_balanced": 0.4,
            "logos_x_band": "MID",
            "logos_quadrant": "Q2",
            "logos_x_index_0_100": 50,
            "logos_y_fragility_0_100": 55,
        },
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "C2=GREEN_HOLD · logos_x=MID quad=Q2 [NON_GATING] · no investment advice.",
            "schema_version": "public-event.v1",
            "event_id": "showroom-test-logos",
            "source": "ops_showroom_bundle_v1",
            "system_status": "online",
            "active_strategies_count": 1,
            "delayed_metrics": {
                "delay_seconds": 180,
                "as_of_utc": "2026-04-03T11:57:00+00:00",
                "logos_x_index_0_100": 50,
                "logos_x_band": "MID",
                "logos_quadrant": "Q2",
                "logos_y_fragility_0_100": 55,
            },
            "direction_abstract": "flat",
            "disclaimer_ref": "jemaai_showroom_v1",
            "last_ok_utc": "2026-04-03T12:00:00+00:00",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_showroom_ux_optional_fields(tmp_path: Path) -> None:
    p = tmp_path / "ux.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {},
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "x",
            "schema_version": "public-event.v1",
            "event_id": "e",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
            "delayed_metrics": {"delay_seconds": 180},
            "showroom_display_mode": "attack",
            "showroom_ticker_key": "S_ONLINE_R_INFO_PSD_HOLD_DA_LONG",
            "showroom_reaction_line_ids": ["R_MODE_ATK_01", "R_MODE_DEF_01"],
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_rejects_bad_showroom_display_mode(tmp_path: Path) -> None:
    p = tmp_path / "bad_sdm.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "x",
            "schema_version": "public-event.v1",
            "event_id": "e",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
            "showroom_display_mode": "banana",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("showroom_display_mode" in e for e in errs)


def test_validate_rejects_bad_logos_band(tmp_path: Path) -> None:
    p = tmp_path / "bad_logos.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "x",
            "schema_version": "public-event.v1",
            "event_id": "e",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
            "delayed_metrics": {"delay_seconds": 180, "logos_x_band": "WRONG"},
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("logos_x_band" in e for e in errs)


def test_validate_accepts_logos_graph_meta_present(tmp_path: Path) -> None:
    p = tmp_path / "with_graph_meta.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {
            "logos_graph_meta": {
                "present": True,
                "schema": "showroom_logos_graph_meta_v1",
                "hypothesis_tier": "B",
                "source_schema": "logos_corpus_graph_bundle_v1",
                "dedupe_bundle_key_sha256": "a" * 64,
                "ts_utc": "2026-04-03T11:00:00Z",
                "nodes_line_count": 10,
                "edges_line_count": 20,
            },
            "track_b_non_gating": True,
            "logos_freshness_staleness_seconds": 3600,
            "logos_freshness_generated_at_utc": "2026-04-03T12:00:00Z",
        },
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "C2=GREEN_HOLD | logos_graph_bundle=B [NON_GATING] | no investment advice.",
            "schema_version": "public-event.v1",
            "event_id": "showroom-graph-meta",
            "source": "ops_showroom_bundle_v1",
            "system_status": "online",
            "active_strategies_count": 1,
            "delayed_metrics": {
                "delay_seconds": 180,
                "as_of_utc": "2026-04-03T11:57:00+00:00",
                "logos_graph_bundle_present": True,
                "logos_graph_nodes_line_count": 10,
                "logos_graph_edges_line_count": 20,
                "logos_graph_bundle_dedupe_sha256": "a" * 64,
                "logos_graph_bundle_ts_utc": "2026-04-03T11:00:00Z",
                "logos_graph_staleness_seconds": 3600,
                "logos_freshness_sidecar_generated_at_utc": "2026-04-03T12:00:00Z",
            },
            "direction_abstract": "flat",
            "disclaimer_ref": "jemaai_showroom_v1",
            "last_ok_utc": "2026-04-03T12:00:00+00:00",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_rejects_logos_graph_meta_rationale(tmp_path: Path) -> None:
    p = tmp_path / "bad_rationale.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "observability": {
            "logos_graph_meta": {
                "present": True,
                "schema": "showroom_logos_graph_meta_v1",
                "hypothesis_tier": "B",
                "dedupe_bundle_key_sha256": "b" * 64,
                "ts_utc": "2026-04-03T11:00:00Z",
                "rationale": "secret sauce narrative",
            },
            "track_b_non_gating": True,
        },
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "x",
            "schema_version": "public-event.v1",
            "event_id": "e",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
            "delayed_metrics": {
                "delay_seconds": 180,
                "logos_graph_bundle_present": True,
                "logos_graph_bundle_dedupe_sha256": "b" * 64,
            },
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("forbidden key: rationale" in e for e in errs)


def test_validate_rejects_logos_graph_present_mismatch(tmp_path: Path) -> None:
    p = tmp_path / "mismatch.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "observability": {
            "logos_graph_meta": {
                "present": True,
                "schema": "showroom_logos_graph_meta_v1",
                "hypothesis_tier": "B",
                "source_schema": "logos_corpus_graph_bundle_v1",
                "dedupe_bundle_key_sha256": "c" * 64,
                "ts_utc": "2026-04-03T11:00:00Z",
            },
            "track_b_non_gating": True,
        },
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "x",
            "schema_version": "public-event.v1",
            "event_id": "e",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
            "delayed_metrics": {"delay_seconds": 180, "logos_graph_bundle_present": False},
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("must agree" in e for e in errs)


def test_validate_rejects_balance_leak(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "balance_total_usdt leak",
            "schema_version": "public-event.v1",
            "event_id": "x",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("forbidden token" in e for e in errs)


def _minimal_public_event() -> dict:
    return {
        "timestamp": "2026-04-03T12:00:00+00:00",
        "active_character_id": "dragon_quant",
        "risk_level": "INFO",
        "public_signal_direction": "HOLD",
        "abstract_reason": "C2=GREEN_HOLD · no investment advice.",
        "schema_version": "public-event.v1",
        "event_id": "showroom-topology-001",
        "source": "ops_showroom_bundle_v1",
        "system_status": "online",
        "active_strategies_count": 1,
        "delayed_metrics": {"delay_seconds": 180, "as_of_utc": "2026-04-03T11:57:00+00:00"},
        "direction_abstract": "flat",
        "disclaimer_ref": "jemaai_showroom_v1",
        "last_ok_utc": "2026-04-03T12:00:00+00:00",
    }


def test_validate_accepts_topology_radar_observability(tmp_path: Path) -> None:
    p = tmp_path / "topology_ok.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {
            "topology_radar_snapshot_present": True,
            "topology_radar_snapshot_generated_at_utc": "2026-05-13T12:00:00Z",
            "topology_radar_snapshot_stale_after_utc": "2026-05-14T00:00:00Z",
            "topology_radar_snapshot_hypo_banner": "[HYPO] Meaning-graph drift snapshot (read-only)",
            "topology_radar_snapshot_artifact_ref_count": 2,
            "topology_radar_snapshot_no_trade_signals": True,
            "topology_radar_snapshot_disclaimer_ref": "jemaai_showroom_v1",
            "topology_radar_snapshot_stub": False,
        },
        "public_ui": {
            "schema": "showroom_public_ui_v1",
            "direction_abstract": "flat",
            "direction_source": "c2",
            "c2_lamp": "GREEN",
            "ops_fusion_ok": True,
            "return_pct_vs_baseline": None,
            "has_return_pct": False,
            "unrealized_pnl_pct_of_equity": None,
            "has_unrealized_pct": False,
            "baseline_mode": "none",
            "unified_score_balanced": 0.4,
        },
        "public_event_v1": _minimal_public_event(),
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_rejects_topology_radar_bad_disclaimer(tmp_path: Path) -> None:
    p = tmp_path / "topology_bad_disc.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {
            "topology_radar_snapshot_present": True,
            "topology_radar_snapshot_generated_at_utc": "2026-05-13T12:00:00Z",
            "topology_radar_snapshot_stale_after_utc": "2026-05-14T00:00:00Z",
            "topology_radar_snapshot_hypo_banner": "[HYPO] x",
            "topology_radar_snapshot_artifact_ref_count": 1,
            "topology_radar_snapshot_no_trade_signals": True,
            "topology_radar_snapshot_disclaimer_ref": "wrong_ref",
            "topology_radar_snapshot_stub": True,
        },
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": _minimal_public_event(),
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("topology_radar_snapshot_disclaimer_ref" in e for e in errs)


def test_validate_rejects_topology_radar_present_false_with_extra_keys(tmp_path: Path) -> None:
    p = tmp_path / "topology_false_extra.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {
            "topology_radar_snapshot_present": False,
            "topology_radar_snapshot_stub": False,
        },
        "public_ui": {"schema": "showroom_public_ui_v1"},
        "public_event_v1": _minimal_public_event(),
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("must not be set when topology_radar_snapshot_present is false" in e for e in errs)
