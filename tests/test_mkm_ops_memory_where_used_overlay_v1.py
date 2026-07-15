"""Where-used ops memory overlay → resume pack pin ([HYPO])."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    COMMANDER_DEFAULT_RESUME_NODES,
    LANE_OPS_PACKS,
    WHERE_USED_JSON_SPECS,
    build_json_slice_node_entry,
    build_where_used_overlay_nodes,
    nodes_for_resume,
)


def test_where_used_overlay_builds() -> None:
    pin = ROOT / "docs/final/artifacts/mkm_ops_pin_where_used_gate_v1_latest.json"
    if not pin.is_file():
        pytest.skip("where_used pin missing")
    nodes = build_where_used_overlay_nodes(ROOT)
    assert "prism_ops_where_used_gate" in nodes
    entry = nodes["prism_ops_where_used_gate"]
    assert entry["slice_kind"] == "json_pointer"
    assert entry["overlay_role"] == "where_used_v1"
    assert "coverage_ok" in entry["must_keep_tags"]
    assert "resolve_mkm_where_used_v1.py" in entry["must_keep_tags"]
    assert "synthesis_ok" in entry["must_keep_tags"]
    built = build_json_slice_node_entry(ROOT, WHERE_USED_JSON_SPECS[0])
    assert built["char_count"] > 0


def test_where_used_in_commander_and_infra_packs() -> None:
    assert "prism_ops_where_used_gate" in COMMANDER_DEFAULT_RESUME_NODES
    assert "prism_ops_where_used_gate" in LANE_OPS_PACKS["infra"]


def test_where_used_resume_link_known_topic() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_mkm_chat_resume_pack_v1 import _where_used_resume_link  # noqa: E402

    link = _where_used_resume_link(ROOT, "ollama")
    assert link is not None
    assert link["topic"] == "ollama"
    assert link["registry"].endswith("mkm_where_used_registry_v1.json")
    assert isinstance(link.get("ssot_paths"), list)
    assert link.get("reproduce")


def test_where_used_resume_link_unknown_topic() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_mkm_chat_resume_pack_v1 import _where_used_resume_link  # noqa: E402

    assert _where_used_resume_link(ROOT, "not_a_registry_topic_xyz") is None


def test_commander_default_resume_includes_where_used_when_indexed() -> None:
    pin = ROOT / "docs/final/artifacts/mkm_ops_pin_where_used_gate_v1_latest.json"
    index_path = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    if not pin.is_file() or not index_path.is_file():
        pytest.skip("index or pin missing")
    import json

    index = json.loads(index_path.read_text(encoding="utf-8"))
    # Ensure overlay present in-memory even if index stale
    overlay = build_where_used_overlay_nodes(ROOT)
    index.setdefault("nodes", {}).update(overlay)
    selected = nodes_for_resume(
        index, top_n=8, lane=None, root=ROOT, commander_default=True
    )
    ids = [nid for nid, _ in selected]
    assert "prism_ops_where_used_gate" in ids
