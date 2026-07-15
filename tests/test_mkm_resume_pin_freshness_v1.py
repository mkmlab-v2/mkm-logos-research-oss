# -*- coding: utf-8 -*-
"""P0.3 resume pin freshness + checkpoint contradiction."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_FRESH = ROOT / "scripts" / "mkm_resume_pin_freshness_v1.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _FRESH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_same_continuity_divergent_status_flags_contradiction():
    mod = _load("fresh_lib_cont")
    ckpts = [
        {
            "stamp_utc": "2026-07-15T10:00:00Z",
            "message": "continuity=demo-x · widget pipeline DONE exit0",
            "continuity_id": "demo-x",
        },
        {
            "stamp_utc": "2026-07-15T09:00:00Z",
            "message": "continuity=demo-x · widget pipeline OPEN blocked",
            "continuity_id": "demo-x",
        },
    ]
    hits = mod.detect_checkpoint_contradictions(ckpts)
    assert len(hits) == 1
    assert hits[0]["collision_reason"] == "same_continuity_divergent_status"
    assert hits[0]["contradicts_prior_checkpoint"] is True


def test_same_continuity_same_polarity_burst_not_contradiction():
    mod = _load("fresh_lib_burst")
    ckpts = [
        {
            "stamp_utc": "2026-07-15T07:44:02Z",
            "message": "continuity=acodeai-homepage-close-2026-07-15 · a-codeai homepage+policy live DONE; next Paddle",
            "continuity_id": "acodeai-homepage-close-2026-07-15",
        },
        {
            "stamp_utc": "2026-07-15T07:43:48Z",
            "message": "continuity=acodeai-homepage-close-2026-07-15 · a-codeai homepage+policy LIVE DONE: deploy exit0",
            "continuity_id": "acodeai-homepage-close-2026-07-15",
        },
    ]
    hits = mod.detect_checkpoint_contradictions(ckpts)
    assert hits == []


def test_polarity_conflict_with_topic_overlap():
    mod = _load("fresh_lib_pol")
    ckpts = [
        {
            "stamp_utc": "2026-07-15T10:00:00Z",
            "message": "P0.3 pin freshness DONE exit0 pytest",
            "continuity_id": "",
        },
        {
            "stamp_utc": "2026-07-15T09:00:00Z",
            "message": "P0.3 pin freshness OPEN blocked pytest",
            "continuity_id": "",
        },
    ]
    hits = mod.detect_checkpoint_contradictions(ckpts)
    assert hits
    assert hits[0]["collision_reason"] in (
        "polarity_conflict+topic_overlap",
        "polarity_conflict",
    )


def test_stale_advisory_when_age_exceeds_max():
    mod = _load("fresh_lib_stale")
    policy = {"default_max_age_days": 3, "max_age_days_by_node_id": {}}
    now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    row = mod.build_pin_freshness_row(
        node_id="prism_ops_lane_infra",
        pin={"file_path": "MISSION_LOG.md"},
        root=ROOT,
        policy=policy,
        index_doc={"last_updated_utc": "2026-07-01T00:00:00Z"},
        checkpoints=[],
        now=now,
    )
    assert row["stale_advisory"] is True
    assert row["age_days"] > 3


def test_fresh_pin_not_stale():
    mod = _load("fresh_lib_fresh")
    policy = {"default_max_age_days": 7, "max_age_days_by_node_id": {}}
    now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    ckpts = [{"stamp_utc": "2026-07-15T11:00:00Z", "message": "recent", "continuity_id": ""}]
    row = mod.build_pin_freshness_row(
        node_id="prism_ops_central_checkpoint",
        pin={"file_path": "docs/final/CENTRAL_AGENT_MEMORY_V1.md"},
        root=ROOT,
        policy={"default_max_age_days": 7, "max_age_days_by_node_id": {"prism_ops_central_checkpoint": 3}},
        index_doc={},
        checkpoints=ckpts,
        now=now,
    )
    assert row["stale_advisory"] is False
    assert row["age_source"] == "newest_checkpoint"


def test_build_freshness_report_schema_fields(tmp_path: Path):
    mod = _load("fresh_lib_report")
    pins = [
        {
            "node_id": "prism_ops_central_checkpoint",
            "age_days": 0.5,
            "max_age_days": 3,
            "stale_advisory": False,
            "as_of_utc": "2026-07-15T10:00:00Z",
            "age_source": "newest_checkpoint",
        }
    ]
    report = mod.build_freshness_report(pins, [], l0_l2_claim_gaps=[])
    assert report["schema"] == "mkm_resume_pin_freshness_v1"
    assert report["send_gate"] == "HOLD"
    assert report["advisory_summary"]["stale_pin_count"] == 0
    assert report["advisory_summary"]["l0_l2_claim_gap_count"] == 0
    assert report["l0_l2_claim_gaps"] == []
    out = tmp_path / "fresh.json"
    mod.write_freshness_latest(report, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema"] == "mkm_resume_pin_freshness_v1"


def test_annotate_ops_pins_adds_freshness_fields(tmp_path: Path):
    mod = _load("fresh_lib_annotate")
    central = tmp_path / "CENTRAL.md"
    central.write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "<!-- CENTRAL checkpoint block -->\n"
        "- **2026-07-15T10:00:00Z** — continuity=test-alpha · alpha DONE\n"
        "- **2026-07-15T09:00:00Z** — continuity=test-alpha · alpha OPEN\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )
    pins = [{"node_id": "prism_ops_central_checkpoint", "essence": "ckpt", "file_path": "CENTRAL.md"}]
    enriched, contradictions, gaps = mod.annotate_ops_pins_freshness(
        pins,
        tmp_path,
        policy={"default_max_age_days": 7, "max_age_days_by_node_id": {"prism_ops_central_checkpoint": 3}},
        index_doc={},
        central_text=central.read_text(encoding="utf-8"),
        now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert enriched[0]["max_age_days"] == 3
    assert "age_days" in enriched[0]
    assert contradictions
    assert gaps == []


def test_must_keep_alone_does_not_trigger_l0_l2_gap(tmp_path: Path):
    mod = _load("fresh_lib_must_keep")
    pins = [
        {
            "node_id": "prism_ops_demo",
            "essence": "advisory coordinate pin only",
            "must_keep_tags": ["PASS", "DONE", "exit0"],
            "file_path": "MISSION_LOG.md",
        }
    ]
    gaps = mod.detect_l0_l2_claim_gaps(pins, tmp_path)
    assert gaps == []


def test_essence_pass_without_l2_artifact_flags_gap(tmp_path: Path):
    mod = _load("fresh_lib_l0l2")
    pins = [
        {
            "node_id": "prism_ops_fake_pass",
            "essence": "widget pipeline DONE exit0",
            "must_keep_tags": ["HOLD"],
            "file_path": "MISSION_LOG.md",
        }
    ]
    (tmp_path / "MISSION_LOG.md").write_text("# board\n", encoding="utf-8")
    gaps = mod.detect_l0_l2_claim_gaps(pins, tmp_path)
    assert len(gaps) == 1
    assert gaps[0]["gap_reason"] == "l0_surface_not_l2_evidence"


def test_essence_gold_with_existing_json_no_gap(tmp_path: Path):
    mod = _load("fresh_lib_gold_ok")
    art = tmp_path / "reports"
    art.mkdir()
    target = art / "logos_router_regression_bundle_v1_latest.json"
    target.write_text(json.dumps({"chain_pass": True, "send_gate": "HOLD"}), encoding="utf-8")
    pins = [
        {
            "node_id": "prism_ops_logos_router_regression_bundle",
            "essence": "P21 router regression bundle — bloom guard + gold 12/12 · HOLD",
            "file_path": "reports/logos_router_regression_bundle_v1_latest.json",
        }
    ]
    gaps = mod.detect_l0_l2_claim_gaps(pins, tmp_path)
    assert gaps == []


def test_missing_l2_json_flags_gap(tmp_path: Path):
    mod = _load("fresh_lib_missing_json")
    pins = [
        {
            "node_id": "prism_ops_missing",
            "essence": "bench PASS exit0",
            "file_path": "docs/final/artifacts/does_not_exist_v1_latest.json",
        }
    ]
    gaps = mod.detect_l0_l2_claim_gaps(pins, tmp_path)
    assert len(gaps) == 1
    assert gaps[0]["gap_reason"] == "missing_l2_artifact"
