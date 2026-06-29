"""Tests for web_ops ops_memory overlay + retrieval bench ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    JsonSliceSpec,
    assemble_ops_memory_pins_text,
    build_json_slice_node_entry,
    build_web_ops_overlay_nodes,
    extract_query_relevant_excerpt,
    filter_json_pointers_for_query,
    json_slice_text,
    merge_overlay_nodes,
    nodes_for_resume,
    prism_axis_field_tag,
    resolve_json_pointer,
    resolve_lane_from_topic,
    route_nodes_by_field_tags,
    jaccard_similarity,
    score_text_query_relevance,
    slice_improves_query_jaccard,
    verify_index_sha_drift,
)

OVERLAY = ROOT / "scripts" / "build_mkm_ops_memory_web_ops_overlay_v1.py"
BENCH = ROOT / "scripts" / "bench_mkm_ops_memory_web_ops_retrieval_v1.py"


def test_resolve_json_pointer_nested() -> None:
    doc = {"cost_policy": {"no_gpu_spinup": True}, "gate_pass": True}
    assert resolve_json_pointer(doc, "/gate_pass") is True
    assert resolve_json_pointer(doc, "/cost_policy/no_gpu_spinup") is True


def test_build_json_slice_node_entry(tmp_path: Path) -> None:
    gate = {
        "gate_pass": True,
        "research_only": True,
        "track_wall": "b_track_research",
        "conflict_resolver": {"worst_final_action": "ALLOW_READ"},
        "cost_policy": {"no_gpu_spinup": True, "nebius_prepaid_only": True},
        "operator_hint_ko": "GPU 자동화 금지",
    }
    gate_path = tmp_path / "reports" / "web_ops_regime_gate_v1_latest.json"
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    spec = JsonSliceSpec(
        node_id="test_gate",
        file_path="reports/web_ops_regime_gate_v1_latest.json",
        json_pointers=("/gate_pass", "/cost_policy/no_gpu_spinup"),
        essence="test",
        must_keep_tags=("gate_pass", "no_gpu_spinup"),
    )
    entry = build_json_slice_node_entry(tmp_path, spec)
    assert entry["slice_kind"] == "json_pointer"
    text = json_slice_text(gate, spec.json_pointers)
    assert "no_gpu_spinup" in text


def test_merge_overlay_and_lane_web_ops(tmp_path: Path) -> None:
    base = {
        "schema": "mkm_ops_memory_index_v1",
        "nodes": {
            "prism_ops_mission_log_board": {"priority": 10},
            "prism_ops_central_checkpoint": {"priority": 9},
            "prism_ops_web_ops_regime_gate": {"priority": 6},
            "prism_ops_web_ops_health": {"priority": 5},
        },
    }
    overlay = {"prism_ops_web_ops_regime_gate": {"priority": 6, "field_tags": ["web_ops"]}}
    merged = merge_overlay_nodes(base, overlay)
    assert merged["index_version"] == "1.1"
    lane_ids = [nid for nid, _ in nodes_for_resume(merged, lane="web_ops")]
    assert "prism_ops_web_ops_regime_gate" in lane_ids


def test_filter_json_pointers_for_query() -> None:
    pointers = [
        "/gate_pass",
        "/nebius_balance_usd",
        "/pointer_drift_detected",
        "/research_only",
    ]
    picked = filter_json_pointers_for_query(pointers, "Nebius 잔액 drift")
    assert "/nebius_balance_usd" in picked
    assert "/pointer_drift_detected" in picked
    assert "/research_only" in picked


def test_resolve_lane_from_topic() -> None:
    assert resolve_lane_from_topic("Nebius 잔액 prepaid") == "web_ops"
    assert resolve_lane_from_topic("GPU infra ollama") == "infra"
    assert resolve_lane_from_topic("hello only") is None


def test_route_nodes_by_field_tags() -> None:
    index = {
        "nodes": {
            "a": {"priority": 5, "field_tags": ["web_ops"], "essence": "Nebius gate"},
            "b": {"priority": 3, "field_tags": ["ms"], "essence": "MS row"},
        }
    }
    hits = route_nodes_by_field_tags(index, "Nebius web_ops cost")
    assert hits[0][0] == "a"

    hits_ko = route_nodes_by_field_tags(index, "네비우스 잔액 감사")
    assert hits_ko and hits_ko[0][0] == "a"


def test_route_regime_action_queries() -> None:
    index = {
        "nodes": {
            "prism_ops_web_ops_regime_gate": {
                "priority": 6,
                "field_tags": ["web_ops", "regime_action"],
                "essence": "ALLOW_READ HOLD_PAYMENT gate",
            },
            "prism_ops_web_ops_health": {
                "priority": 5,
                "field_tags": ["web_ops", "health", "regime_action"],
                "essence": "worst_final_action health",
            },
            "prism_ops_lane_ms": {
                "priority": 7,
                "field_tags": ["ms"],
                "essence": "MS only",
            },
        }
    }
    allow_hits = route_nodes_by_field_tags(index, "ALLOW_READ read_only_dashboard")
    assert allow_hits
    assert allow_hits[0][0] == "prism_ops_web_ops_regime_gate"

    hold_hits = route_nodes_by_field_tags(index, "HOLD_PAYMENT payment risk")
    assert hold_hits
    assert "prism_ops_web_ops_regime_gate" in {nid for nid, _ in hold_hits}


def test_prism_axis_tag_blocks_bare_letter_leak() -> None:
    index = {
        "nodes": {
            "reg_a": {
                "priority": 5,
                "field_tags": ["s", prism_axis_field_tag("S"), "prism_entry_a"],
                "essence": "entry a",
                "file_path": "docs/a.md",
            },
            "reg_b": {
                "priority": 5,
                "field_tags": [prism_axis_field_tag("S"), "prism_entry_b"],
                "essence": "entry b",
                "file_path": "docs/b.md",
            },
        }
    }
    vague = route_nodes_by_field_tags(index, "web_ops regime gate s", max_nodes=8)
    assert len(vague) <= 1  # bare "s" must not fan-out all S-axis nodes

    explicit = route_nodes_by_field_tags(
        index, "prism S SSOT prism_axis_s", max_nodes=8
    )
    assert explicit
    assert explicit[0][0] in {"reg_a", "reg_b"}


def test_slice_improves_query_jaccard_gate() -> None:
    query = "web_ops regime gate Nebius"
    header = "web_ops regime gate Nebius summary"
    noise = "unrelated filler " * 40
    assert not slice_improves_query_jaccard(query, header, noise)
    sparse_header = "web_ops regime gate summary"
    helpful = "Nebius"
    assert slice_improves_query_jaccard(query, sparse_header, helpful)


def test_repair_slice_skipped_when_essence_more_relevant(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_ops_memory_index_lib_v1 import extract_node_repair_slice

    doc = tmp_path / "docs" / "note.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# header\n\noracle prophecy lane only in body\n\nunrelated filler text\n",
        encoding="utf-8",
    )
    node = {
        "essence": "oracle prophecy inception align",
        "file_path": "docs/note.md",
        "slice_kind": "registry_chunk",
    }
    slice_text = extract_node_repair_slice(
        tmp_path,
        node,
        "oracle prophecy inception align",
        max_chars=400,
    )
    assert slice_text == ""


def test_extract_query_relevant_excerpt_skips_noise_header() -> None:
    body = (
        "# Generic header noise\n\n"
        "Unrelated boilerplate paragraph.\n\n"
        "web_ops regime gate probe with gate_pass and Nebius balance.\n\n"
        "Another unrelated tail section.\n"
    )
    excerpt = extract_query_relevant_excerpt(
        body,
        "web_ops regime gate Nebius",
        max_chars=200,
    )
    assert "web_ops" in excerpt
    assert "gate_pass" in excerpt
    assert score_text_query_relevance(excerpt, "web_ops regime gate Nebius") >= 3
    assert "Generic header noise" not in excerpt


def test_assemble_ops_memory_pins_text_respects_total_budget(tmp_path: Path) -> None:
    body = tmp_path / "docs" / "big.md"
    body.parent.mkdir(parents=True)
    body.write_text("x" * 5000, encoding="utf-8")
    routed = [
        (
            "n1",
            {
                "essence": "one",
                "must_keep_tags": ["research_only"],
                "file_path": "docs/big.md",
                "slice_kind": "registry_chunk",
            },
        ),
        (
            "n2",
            {
                "essence": "two",
                "must_keep_tags": ["research_only"],
                "file_path": "docs/big.md",
                "slice_kind": "registry_chunk",
            },
        ),
    ]
    text = assemble_ops_memory_pins_text(
        tmp_path,
        routed,
        include_slice=True,
        slice_max_chars=1200,
        max_total_chars=900,
    )
    assert len(text) <= 950


def test_filter_pointers_regime_action() -> None:
    pointers = [
        "/gate_pass",
        "/conflict_resolver/worst_final_action",
        "/cost_policy/no_new_billing_charges",
        "/operator_hint_ko",
        "/research_only",
    ]
    picked = filter_json_pointers_for_query(pointers, "HOLD_PAYMENT payment risk")
    assert "/cost_policy/no_new_billing_charges" in picked
    assert "/operator_hint_ko" in picked


def test_sha_drift_detects_change(tmp_path: Path) -> None:
    gate_path = tmp_path / "reports" / "gate.json"
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text('{"gate_pass": true, "research_only": true}', encoding="utf-8")
    index = {
        "nodes": {
            "n1": {
                "slice_kind": "json_pointer",
                "file_path": "reports/gate.json",
                "json_pointers": ["/gate_pass"],
                "content_sha256_prefix": "deadbeef00000000",
            }
        }
    }
    errors = verify_index_sha_drift(tmp_path, index)
    assert errors and "HOLD_POINTER_DRIFT" in errors[0]


def test_overlay_cli_merges_into_index(tmp_path: Path) -> None:
    gate = {
        "gate_pass": True,
        "research_only": True,
        "track_wall": "b_track_research",
        "conflict_resolver": {"worst_final_action": "ALLOW_READ"},
        "cost_policy": {
            "no_gpu_spinup": True,
            "no_new_billing_charges": True,
            "nebius_prepaid_only": True,
        },
        "operator_hint_ko": "hold",
    }
    health = {
        "health_ok": True,
        "gate_pass": True,
        "research_only": True,
        "nebius_balance_usd": 25.0,
        "pointer_drift_detected": False,
        "observation_source": "dry_run_json",
        "worst_final_action": "ALLOW_READ",
    }
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    (reports / "web_ops_regime_gate_v1_latest.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )
    (reports / "web_ops_regime_health_summary_v1_latest.json").write_text(
        json.dumps(health), encoding="utf-8"
    )
    index_path = tmp_path / "storage" / "meta" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps({"schema": "mkm_ops_memory_index_v1", "nodes": {}}),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(OVERLAY),
            "--workspace-root",
            str(tmp_path),
            "--index",
            str(index_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    loaded = json.loads(index_path.read_text(encoding="utf-8"))
    assert "prism_ops_web_ops_regime_gate" in loaded["nodes"]
    assert "prism_ops_web_ops_health" in loaded["nodes"]


def test_retrieval_bench_writes_json(tmp_path: Path) -> None:
    gate = {
        "gate_pass": True,
        "research_only": True,
        "track_wall": "b_track_research",
        "conflict_resolver": {"worst_final_action": "ALLOW_READ"},
        "cost_policy": {
            "no_gpu_spinup": True,
            "no_new_billing_charges": True,
            "nebius_prepaid_only": True,
        },
        "operator_hint_ko": "x",
    }
    health = {
        "health_ok": True,
        "gate_pass": True,
        "research_only": True,
        "nebius_balance_usd": 25.0,
        "pointer_drift_detected": False,
        "observation_source": "dry_run_json",
        "worst_final_action": "ALLOW_READ",
    }
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    gate_path = reports / "web_ops_regime_gate_v1_latest.json"
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    (reports / "web_ops_regime_health_summary_v1_latest.json").write_text(
        json.dumps(health), encoding="utf-8"
    )

    nodes = {}
    for spec_entry in build_web_ops_overlay_nodes(tmp_path).items():
        nodes[spec_entry[0]] = spec_entry[1]
    index_path = tmp_path / "index.json"
    index_path.write_text(
        json.dumps({"nodes": nodes}, ensure_ascii=False),
        encoding="utf-8",
    )
    out_path = tmp_path / "bench.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--workspace-root",
            str(tmp_path),
            "--index",
            str(index_path),
            "--gate-json",
            str(gate_path),
            "--out",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["scenario_count"] == 20
    assert "raw" in doc["aggregate"]
    assert "repair_v2" in doc["aggregate"]
