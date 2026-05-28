#!/usr/bin/env python3
"""Build pet observation bridges from memory slots + device bridge fixture ([HYPO])."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_SLOTS = ROOT / "reports/pet_companion_memory_slots_latest.json"
DEFAULT_SLOTS_FALLBACK = ART / "fixtures/pet_companion_memory_slots_demo_fallback_v1.json"
DEFAULT_FIXTURE = ART / "fixtures/pet_companion_device_memory_bridge_v1_fixture.json"
DEFAULT_OUT = ART / "pet_companion_observation_bridge_registry_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slot_to_bridge(profile_id: str, slot: dict[str, Any]) -> dict[str, Any]:
    slot_id = str(slot.get("slot_id") or f"{profile_id}:{slot.get('type')}")
    slot_type = str(slot.get("type") or "observation")
    value = str(slot.get("value") or "")
    keywords = [str(k) for k in (slot.get("keywords") or []) if k]
    obs_id = slot_id.replace(":", "_")
    nodes: list[dict[str, Any]] = [
        {
            "node_id": f"node_profile_{profile_id}",
            "kind": "profile_ref",
            "label_ko": profile_id,
            "profile_id": profile_id,
        },
        {
            "node_id": f"node_obs_{obs_id}",
            "kind": "observation_ref",
            "label_ko": value,
            "observation_id": obs_id,
        },
    ]
    for i, kw in enumerate(keywords[:8]):
        nodes.append(
            {
                "node_id": f"node_kw_{obs_id}_{i}",
                "kind": "keyword",
                "label_ko": kw,
            }
        )
    return {
        "schema": "pet_companion_observation_bridge_v1",
        "hypothesis_tier": "B",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_veterinary_diagnosis_claim": True,
            "generation_method": "slots_projection_v1",
        },
        "query": {
            "concept_id": f"obs:{slot_type}",
            "label_ko": value,
            "profile_id": profile_id,
            "scenario": slot_type,
        },
        "keywords": keywords,
        "nodes": nodes,
        "paths": [
            {
                "path_id": f"path_{obs_id}_checklist",
                "note_ko": "온디바이스 관측→체크리스트 힌트 (B-track, 비처방)",
                "steps": [
                    {"from": f"node_profile_{profile_id}", "to": f"node_obs_{obs_id}", "relation": "HAS_OBSERVATION"},
                    {"from": f"node_obs_{obs_id}", "to": f"node_kw_{obs_id}_0", "relation": "KEYWORD_ANCHOR"},
                ],
            }
        ],
    }


def _fixture_hints_bridge(fixture: dict[str, Any]) -> dict[str, Any] | None:
    resp = fixture.get("mock_response") if isinstance(fixture.get("mock_response"), dict) else {}
    hints = resp.get("local_graph_update_hints") if isinstance(resp.get("local_graph_update_hints"), dict) else {}
    nodes_up = [str(x) for x in (hints.get("suggested_nodes_to_upsert") or []) if x]
    if not nodes_up:
        return None
    req = fixture.get("mock_request") if isinstance(fixture.get("mock_request"), dict) else {}
    profile_id = str(req.get("profile_id") or "pet-demo-001")
    scenario = str(req.get("scenario") or "health_check")
    question = str(req.get("raw_user_question_masked") or "")
    extra_kw = ["응급", "병원", "산책", "패턴", "건강", "다리", "불편", scenario, profile_id]
    nodes: list[dict[str, Any]] = [
        {"node_id": "node_profile_fixture", "kind": "profile_ref", "label_ko": profile_id, "profile_id": profile_id},
        {"node_id": "node_scenario_fixture", "kind": "scenario_ref", "label_ko": scenario, "scenario": scenario},
    ]
    for i, label in enumerate(nodes_up):
        nodes.append(
            {
                "node_id": f"node_hint_{i}",
                "kind": "observation_ref",
                "label_ko": label,
                "observation_id": f"hint_{i}",
            }
        )
    edges = hints.get("suggested_edges_to_link") or []
    steps = []
    for j, edge in enumerate(edges if isinstance(edges, list) else []):
        if not isinstance(edge, dict):
            continue
        steps.append(
            {
                "from": str(edge.get("source") or "node_profile_fixture"),
                "to": str(edge.get("target") or f"node_hint_{j}"),
                "relation": str(edge.get("relation") or "LINK"),
            }
        )
    return {
        "schema": "pet_companion_observation_bridge_v1",
        "hypothesis_tier": "B",
        "policy": {"research_only": True, "non_gating": True, "generation_method": "fixture_hints_v1"},
        "query": {"concept_id": f"obs:fixture_{scenario}", "label_ko": question, "profile_id": profile_id, "scenario": scenario},
        "keywords": nodes_up + extra_kw,
        "nodes": nodes,
        "paths": [{"path_id": "path_fixture_hints", "steps": steps, "note_ko": "device bridge local_graph_update_hints"}],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slots-json", type=Path, default=DEFAULT_SLOTS)
    ap.add_argument("--fixture-json", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    slots_path = args.slots_json if args.slots_json.is_absolute() else ROOT / args.slots_json
    fixture_path = args.fixture_json if args.fixture_json.is_absolute() else ROOT / args.fixture_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    bridge_paths: list[Path] = []
    entries: list[dict[str, Any]] = []

    slots_doc: dict[str, Any] | None = None
    if slots_path.is_file():
        slots_doc = json.loads(slots_path.read_text(encoding="utf-8-sig"))
    if not slots_doc or int(slots_doc.get("slots_count") or 0) == 0:
        fb_path = DEFAULT_SLOTS_FALLBACK if DEFAULT_SLOTS_FALLBACK.is_absolute() else ROOT / DEFAULT_SLOTS_FALLBACK
        if fb_path.is_file():
            slots_doc = json.loads(fb_path.read_text(encoding="utf-8-sig"))

    if isinstance(slots_doc, dict):
        for profile_id, slot_list in (slots_doc.get("slots_by_profile") or {}).items():
            if not isinstance(slot_list, list):
                continue
            for slot in slot_list:
                if not isinstance(slot, dict):
                    continue
                bridge = _slot_to_bridge(str(profile_id), slot)
                rel = f"docs/final/artifacts/pet_companion_observation_bridge_{str(slot.get('type'))}_{profile_id}_v1_latest.json"
                path = ROOT / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                bridge_paths.append(path)
                entries.append(
                    {
                        "artifact_path": rel.replace("\\", "/"),
                        "present": True,
                        "concept_id": bridge["query"]["concept_id"],
                        "label_ko": bridge["query"]["label_ko"],
                        "path_count": len(bridge.get("paths") or []),
                        "profile_id": profile_id,
                    }
                )

    if fixture_path.is_file():
        fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
        hint_bridge = _fixture_hints_bridge(fixture)
        if hint_bridge:
            rel = "docs/final/artifacts/pet_companion_observation_bridge_fixture_hints_v1_latest.json"
            path = ROOT / rel
            path.write_text(json.dumps(hint_bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            bridge_paths.append(path)
            entries.append(
                {
                    "artifact_path": rel,
                    "present": True,
                    "concept_id": hint_bridge["query"]["concept_id"],
                    "label_ko": "fixture_graph_hints",
                    "path_count": len(hint_bridge.get("paths") or []),
                    "profile_id": hint_bridge["query"].get("profile_id"),
                }
            )

    if not entries:
        raise SystemExit("no bridges built — provide slots-json or fixture-json")

    doc = {
        "schema": "pet_companion_observation_bridge_registry_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "bridge_count": len(entries),
        "entries": entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "bridge_count": len(entries), "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
