#!/usr/bin/env python3
"""Build JEMA OS coordinate envelope v1 — surface↔kernel pointer bag [HOLD].

  py scripts/build_jema_os_coordinate_envelope_v1.py
  py scripts/build_jema_os_coordinate_envelope_v1.py --read-depth deep --lane oracle
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/jema_os_coordinate_envelope_v1_latest.json"
NO1KMEDI_PUBLIC = ROOT / "projects/no1kmedi/public/data"
HYBRID_CHAIN = ROOT / "reports/logos_hybrid_middleware_chain_v1_latest.json"
UMR_DEFAULT = ROOT / "docs/final/artifacts/universal_multi_res_router_logos_hybrid_chain_v1_latest.json"
BRAND_POINTER = ROOT / "docs/final/artifacts/jema_os_brand_pointer_v1_latest.json"
SHALLOW_HANDOFF = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
REGISTRY_V2 = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
GRAPH_REF = Path("storage/meta/mkm_long_term_memory_graph_v1.json")

LANE_LTM_PRIMARY_CONCEPT: dict[str, str] = {
    "ms": "ms_lane_submission_hold",
    "oracle": "prophecy_research_only_boundary",
    "infra": "infra_solo_scheduler_stack",
    "design": "design_showroom_domain_portfolio",
    "ops": "lane_resume_pack_contract",
}

LANE_SOFTWARE_LAYER: dict[str, str] = {
    "ms": "track_a_ops_adjacent",
    "oracle": "B_track_research",
    "infra": "infra_ops",
    "design": "track_c_showroom",
    "ops": "ops_memory",
}

READ_DEPTH_BINDING: dict[str, dict[str, Any]] = {
    "skim": {
        "resolution_tier": "low_res",
        "required_ltm_depth": 0.15,
        "resume_mode_hint": "standard",
    },
    "deep": {
        "resolution_tier": "high_res",
        "required_ltm_depth": 0.65,
        "resume_mode_hint": "advanced_logos_oracle_lane_only",
    },
    "hold": {
        "resolution_tier": "hold_gate",
        "required_ltm_depth": 0.0,
        "resume_mode_hint": "hold",
    },
}

DOMAIN_POSTIT_DEFAULTS: dict[str, dict[str, Any]] = {
    "logos": {
        "evidence_mode": "HYPO",
        "lane": "B-track",
        "pointer": {"verse_id": "Gen.1.1"},
    },
    "compression": {
        "evidence_mode": "FACT_LOCK",
        "lane": "A-track",
        "pointer": {
            "zone_id": "zone_g_health",
            "codebook_shard_rel": "codebook/shards/zone_g_health.json",
        },
    },
    "sasang": {
        "evidence_mode": "HYPO",
        "lane": "B-track",
        "pointer": {"zone_id": "zone_g_health"},
    },
    "myeongni": {
        "evidence_mode": "HYPO",
        "lane": "B-track",
        "pointer": {"zone_id": "zone_g_health"},
    },
    "enterprise_herbs_formulas": {
        "evidence_mode": "HYPO",
        "lane": "clinical_b",
        "pointer": {"zone_id": "zone_g_health"},
    },
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def map_read_depth(read_depth: str) -> dict[str, Any]:
    key = read_depth.strip().lower()
    if key not in READ_DEPTH_BINDING:
        raise ValueError(f"unsupported read_depth: {read_depth}")
    return {"read_depth": key, **READ_DEPTH_BINDING[key]}


def build_postit_pointer(domain_tag: str) -> dict[str, Any]:
    base = DOMAIN_POSTIT_DEFAULTS.get(domain_tag) or DOMAIN_POSTIT_DEFAULTS["logos"]
    return {
        "schema": "postit_pointer_v1",
        "evidence_mode": base["evidence_mode"],
        "lane": base["lane"],
        "pointer": dict(base["pointer"]),
        "metric_scope": {
            "raw_metric": "alignment_pass_rate(raw)",
            "repair_metric": "alignment_pass_rate(repair_v2)",
            "delta": "repair_v2_minus_raw",
        },
    }


def build_ltm_pin(lane: str) -> dict[str, Any]:
    concept = LANE_LTM_PRIMARY_CONCEPT.get(lane, "lane_resume_pack_contract")
    layer = LANE_SOFTWARE_LAYER.get(lane, "B_track_research")
    return {
        "concept_id": concept,
        "software_layer": layer,
        "inject_policy": "single_node_only",
        "graph_ref": _rel(ROOT / GRAPH_REF),
        "lane": lane,
    }


def build_a2a_peer(lane: str, *, root: Path = ROOT) -> dict[str, Any]:
    brief = root / f"docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
    pointer = _rel(brief) if brief.is_file() else None
    bounded_ref: str | None = None
    bounded_pin: str | None = None
    ltm_hint_cross: dict[str, Any] | None = None
    bounded_path = root / "reports/bounded_lane_loop_v1_latest.json"
    bounded = _read_json(bounded_path)
    if bounded:
        bounded_ref = _rel(bounded_path)
        bl_lane = str(bounded.get("lane") or "")
        if bl_lane == lane or (lane == "oracle" and bounded.get("peer_handoff_pointer")):
            if not pointer and bounded.get("peer_handoff_pointer"):
                pointer = str(bounded["peer_handoff_pointer"])
            pin_path = bounded.get("pin_path")
            if isinstance(pin_path, str) and pin_path.strip():
                bounded_pin = pin_path.strip().replace("\\", "/")
            hint = bounded.get("ltm_hint")
            if isinstance(hint, dict):
                ltm_hint_cross = dict(hint)
    row: dict[str, Any] = {
        "optional": True,
        "peer_handoff_pointer": pointer,
        "lane": lane,
    }
    if bounded_ref:
        row["bounded_lane_loop_ref"] = bounded_ref
    if bounded_pin:
        row["bounded_lane_pin_ref"] = bounded_pin
    if ltm_hint_cross:
        row["ltm_hint_cross_ref"] = ltm_hint_cross
    return row


def build_envelope(
    *,
    read_depth: str = "skim",
    lane: str = "oracle",
    hybrid_path: Path = HYBRID_CHAIN,
    umr_path: Path = UMR_DEFAULT,
    root: Path = ROOT,
) -> dict[str, Any]:
    depth = map_read_depth(read_depth)
    hybrid = _read_json(hybrid_path if hybrid_path.is_absolute() else root / hybrid_path)
    umr = _read_json(umr_path if umr_path.is_absolute() else root / umr_path)

    steps = hybrid.get("steps") if isinstance(hybrid.get("steps"), dict) else {}
    umr_step = steps.get("umr_route") or {}
    domain_tag = str(umr.get("domain_tag") or umr_step.get("domain_tag") or "logos")
    epistemic_grade = str(umr.get("epistemic_grade") or "HYPO")

    send_gate = str(hybrid.get("send_gate") or umr.get("send_gate") or "HOLD")
    research_only = bool(hybrid.get("research_only", True))
    track_a = bool(hybrid.get("track_a_promotion_allowed", False))

    slot_v2 = umr.get("domain_plugin_slot_v2")
    if not isinstance(slot_v2, dict):
        slot_v2 = umr_step.get("domain_plugin_slot_v2")
    registry_ref = umr.get("jema_os_plugin_registry_v2_ref") or umr_step.get(
        "jema_os_plugin_registry_v2_ref"
    )
    if not registry_ref and REGISTRY_V2.is_file():
        registry_ref = _rel(REGISTRY_V2)

    envelope: dict[str, Any] = {
        "schema": "jema_os_coordinate_envelope_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "send_gate": send_gate if send_gate in ("HOLD", "OPEN") else "HOLD",
        "research_only": research_only,
        "track_a_promotion_allowed": track_a,
        "read_depth": depth["read_depth"],
        "umr_binding": {
            "resolution_tier": depth["resolution_tier"],
            "required_ltm_depth": depth["required_ltm_depth"],
            "domain_tag": domain_tag,
            "epistemic_grade": epistemic_grade
            if epistemic_grade in ("FACT", "HYPO", "VISION", "FORBIDDEN")
            else "HYPO",
            "umr_artifact_ref": _rel(umr_path if umr_path.is_absolute() else root / umr_path),
            "resume_mode_hint": depth["resume_mode_hint"],
        },
        "postit_pointer": build_postit_pointer(domain_tag),
        "ltm_pin": build_ltm_pin(lane),
        "a2a_peer": build_a2a_peer(lane, root=root),
        "fail_comp_004_guard": {
            "compression_kpi_weight_in_inference": 0,
            "lens_score_headline_merge": False,
            "collapsed_combined_score": None,
            "notes_ko": "압축·렌즈·추론 raw·실매매 가중치 헤드라인 합산 금지",
        },
        "surface_hints": {
            "hub_llm_enabled": False,
            "allowed_surfaces": ["hub", "enterprise", "mkmlife", "logos.jema-ai.com"],
        },
        "provenance": {
            "hybrid_middleware_chain_ref": _rel(
                hybrid_path if hybrid_path.is_absolute() else root / hybrid_path
            ),
            "brand_pointer_ref": _rel(BRAND_POINTER),
            "shallow_handoff_ref": _rel(SHALLOW_HANDOFF),
        },
        "reproduce": (
            f"py scripts/build_jema_os_coordinate_envelope_v1.py "
            f"--read-depth {depth['read_depth']} --lane {lane}"
        ),
    }
    if isinstance(slot_v2, dict):
        envelope["domain_plugin_slot_v2"] = slot_v2
    if registry_ref:
        envelope["jema_os_plugin_registry_v2_ref"] = str(registry_ref)
    return envelope


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mirror_no1kmedi(doc: dict[str, Any], *, read_depth: str) -> list[Path]:
    depth = read_depth.strip().lower()
    paths = [
        NO1KMEDI_PUBLIC / f"jema_os_coordinate_envelope_{depth}_v1.json",
    ]
    if depth == "skim":
        paths.append(NO1KMEDI_PUBLIC / "jema_os_coordinate_envelope_v1.json")
    written: list[Path] = []
    for path in paths:
        _write_json(path, doc)
        written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--read-depth", choices=sorted(READ_DEPTH_BINDING), default="skim")
    ap.add_argument("--lane", choices=sorted(LANE_LTM_PRIMARY_CONCEPT), default="oracle")
    ap.add_argument("--hybrid-json", type=Path, default=HYBRID_CHAIN)
    ap.add_argument("--umr-json", type=Path, default=UMR_DEFAULT)
    ap.add_argument("--mirror-no1kmedi", action="store_true")
    ap.add_argument(
        "--mirror-all-depths",
        action="store_true",
        help="Write skim+deep (+ hold) to no1kmedi public/data",
    )
    args = ap.parse_args()

    depths = sorted(READ_DEPTH_BINDING) if args.mirror_all_depths else [args.read_depth]
    last_doc: dict[str, Any] | None = None
    mirror_paths: list[Path] = []

    for depth in depths:
        doc = build_envelope(
            read_depth=depth,
            lane=args.lane,
            hybrid_path=args.hybrid_json,
            umr_path=args.umr_json,
        )
        last_doc = doc
        if depth == args.read_depth or len(depths) == 1:
            _write_json(args.out, doc)
        if args.mirror_no1kmedi or args.mirror_all_depths:
            mirror_paths.extend(mirror_no1kmedi(doc, read_depth=depth))

    assert last_doc is not None
    payload: dict[str, Any] = {
        "ok": True,
        "out": str(args.out),
        "read_depth": last_doc["read_depth"],
    }
    if mirror_paths:
        payload["mirror_no1kmedi"] = [str(p) for p in mirror_paths]
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
