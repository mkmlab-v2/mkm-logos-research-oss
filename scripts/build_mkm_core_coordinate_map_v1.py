#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build MKM_CORE_MAP — metacog coordinate matrix for Cursor rules diet.

Thin inject surface: IDs + allow/forbid + resolve paths. Not full prose SSOT.
alwaysApply stack is NOT expanded (diet cap). Map is requestable / artifact.

  py scripts/build_mkm_core_coordinate_map_v1.py
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs/final/artifacts/mkm_core_coordinate_map_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/mkm_core_coordinate_map_v1_latest.md"
OUT_REPORT = ROOT / "reports/mkm_core_coordinate_map_v1_latest.md"
MDC = ROOT / ".cursor/rules/mkm-core-coordinate-map-v1.mdc"

ANCHOR_LINES = [
    "이 좌표 지도는 절대 수정·합선이 금지된 하드 제약 격벽이다.",
    "좌표는 포인터다 — 실행 전 해당 SSOT/스크립트를 Resolve(Read/exit0)하라.",
    "ready_for_auto ≠ SEND · Fact-Lock = CONSTITUTION + 스크립트 + exit0 + artifact.",
]

# id | kind | allow|forbid | resolve | must_keep
COORDS: list[dict[str, Any]] = [
    {
        "id": "wall.send_gate",
        "kind": "wall",
        "constraint": "forbid_open_without_commander",
        "resolve": "docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json",
        "must_keep": ["SEND_GATE: HOLD", "narrative_lane_open≠SEND"],
    },
    {
        "id": "wall.ready_for_auto_airlock",
        "kind": "wall",
        "constraint": "ready_for_auto_is_not_send",
        "resolve": "docs/final/artifacts/mkm_middleware_llm_p0_prove_freeze_v1_latest.json",
        "must_keep": ["ready_for_auto_is_not_send", "LIVE: OFF"],
    },
    {
        "id": "wall.track_a_b",
        "kind": "wall",
        "constraint": "no_b_to_a_auto_bridge",
        "resolve": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        "must_keep": ["FAIL-COMP-004", "Track A", "B-track"],
    },
    {
        "id": "wall.lens_non_gating",
        "kind": "wall",
        "constraint": "logos_never_gate_final_action",
        "resolve": "docs/final/LOGOS_METACOG_COORDINATE_OS_V1.md",
        "must_keep": ["NON_GATING", "surviving_axes_SK"],
    },
    {
        "id": "pin.mission_log_board",
        "kind": "pin",
        "constraint": "ops_board_only_no_full_paste",
        "resolve": "MISSION_LOG.md",
        "must_keep": ["prism_ops_mission_log_board"],
    },
    {
        "id": "pin.central_checkpoint",
        "kind": "pin",
        "constraint": "identity_checkpoint_ssot",
        "resolve": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        "must_keep": ["prism_ops_central_checkpoint", "ATHENA_CHECKPOINT"],
    },
    {
        "id": "pin.logos_metacog",
        "kind": "pin",
        "constraint": "metacog_coord_not_predictor",
        "resolve": "docs/final/artifacts/mkm_ops_pin_absolute_balance_conflict_state_v1_latest.json",
        "must_keep": ["prism_ops_logos_metacog_coord", "Absolute Balance≠5th AI"],
    },
    {
        "id": "budget.resume_inject",
        "kind": "budget",
        "constraint": "chars_pins_guardrail_caps",
        "resolve": "docs/final/artifacts/mkm_resume_inject_budget_v1_latest.json",
        "must_keep": ["max_ops_inject_chars", "max_mistake_guardrails"],
    },
    {
        "id": "budget.middleware_prompt",
        "kind": "budget",
        "constraint": "max_prompt_chars_6000_stamp",
        "resolve": "docs/final/artifacts/mkm_resume_inject_budget_v1_latest.json#budgets.middleware_llm",
        "must_keep": ["max_prompt_chars=6000", "sidecar_stamp"],
    },
    {
        "id": "mw.llm_harness_p0",
        "kind": "middleware",
        "constraint": "adapter_compiler_enforcer_stub_default",
        "resolve": "scripts/run_mkm_middleware_llm_harness_v1.py",
        "must_keep": ["provider=stub_default", "citation_lock"],
    },
    {
        "id": "mw.slot_combo",
        "kind": "middleware",
        "constraint": "slot3_humanist_governance_default",
        "resolve": "docs/final/artifacts/mkm_middleware_slot_combo_ablation_v1_latest.json",
        "must_keep": ["no_vector_merge", "slot3_humanist"],
    },
    {
        "id": "reg.where_used",
        "kind": "registry",
        "constraint": "enumerate_before_claim",
        "resolve": "docs/final/artifacts/mkm_where_used_registry_v1.json",
        "must_keep": ["prism_ops_where_used_gate"],
    },
    {
        "id": "reg.logos_inject_whitelist",
        "kind": "registry",
        "constraint": "inject_consumer_whitelist_only",
        "resolve": "docs/final/artifacts/logos_metacog_inject_consumer_registry_v1_latest.json",
        "must_keep": ["whitelist", "NON_GATING"],
    },
    {
        "id": "diet.always_apply_cap",
        "kind": "diet",
        "constraint": "max_always_apply_10_no_new_core_without_review",
        "resolve": "scripts/check_cursor_rules_context_diet_v1.py",
        "must_keep": ["CORE_ALWAYS_APPLY", "requestable_lanes"],
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    missing: list[str] = []
    for c in COORDS:
        path = str(c["resolve"]).split("#", 1)[0]
        if not (ROOT / path).is_file():
            missing.append(path)

    doc = {
        "schema": "mkm_core_coordinate_map_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "label": "MKM_CORE_MAP",
        "purpose_ko": "룰/컨텍스트에 서사 대신 ID·허용금지·Resolve 경로만 주입 (밀도↑·피로↓)",
        "anchor_lines": ANCHOR_LINES,
        "inject_policy": {
            "always_apply_expansion": False,
            "reason_ko": "diet cap — 코어 alwaysApply 추가 금지; requestable mdc + artifact로 Resolve",
            "mdc": ".cursor/rules/mkm-core-coordinate-map-v1.mdc",
            "max_map_md_chars": 4500,
        },
        "coordinates": COORDS,
        "coord_count": len(COORDS),
        "missing_resolve_paths": missing,
        "ok": len(missing) == 0,
        "reproduce": [
            "py scripts/build_mkm_core_coordinate_map_v1.py",
            "py scripts/check_mkm_core_coordinate_map_v1.py --strict",
            "py -m pytest tests/test_mkm_core_coordinate_map_v1.py -q",
        ],
    }
    return doc


def _write_md(doc: dict[str, Any]) -> str:
    lines = [
        "# MKM_CORE_MAP v1",
        "",
        "## Anchor (hard)",
        "",
        *[f"{i}. {a}" for i, a in enumerate(doc["anchor_lines"], 1)],
        "",
        "## Coordinate matrix",
        "",
        "| id | kind | constraint | resolve |",
        "|----|------|------------|---------|",
    ]
    for c in doc["coordinates"]:
        lines.append(
            f"| `{c['id']}` | {c['kind']} | `{c['constraint']}` | `{c['resolve']}` |"
        )
    lines.extend(
        [
            "",
            "## must_keep (sample)",
            "",
            "- SEND_GATE HOLD · ready_for_auto≠SEND · NON_GATING · FAIL-COMP-004",
            "- max_prompt_chars=6000 · no_vector_merge · Absolute Balance≠5th AI",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "py scripts/build_mkm_core_coordinate_map_v1.py",
            "```",
            "",
        ]
    )
    text = "\n".join(lines)
    return text


def _write_mdc(doc: dict[str, Any]) -> None:
    # Keep mdc tiny — anchor + pointer only (Resolve to artifact).
    body = "\n".join(
        [
            "---",
            "description: MKM_CORE_MAP — metacog coordinate matrix (requestable; not alwaysApply)",
            "alwaysApply: false",
            "---",
            "",
            "# MKM_CORE_MAP",
            "",
            doc["anchor_lines"][0],
            doc["anchor_lines"][1],
            doc["anchor_lines"][2],
            "",
            "**Resolve:** `docs/final/artifacts/mkm_core_coordinate_map_v1_latest.json`",
            "",
            "| id | constraint |",
            "|----|------------|",
        ]
    )
    # Only wall+budget rows in mdc to stay tiny
    rows = [
        c
        for c in doc["coordinates"]
        if c["kind"] in ("wall", "budget", "diet")
    ]
    for c in rows:
        body += f"\n| `{c['id']}` | `{c['constraint']}` |"
    body += (
        "\n\nFull matrix + middleware/registry pins: artifact JSON. "
        "Do not paste full MISSION_LOG or CONSTITUTION into chat.\n"
    )
    MDC.parent.mkdir(parents=True, exist_ok=True)
    MDC.write_text(body, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    doc = build()
    md = _write_md(doc)
    doc["map_md_chars"] = len(md)
    if doc["map_md_chars"] > int((doc.get("inject_policy") or {}).get("max_map_md_chars") or 4500):
        doc["ok"] = False
        doc.setdefault("missing_resolve_paths", []).append("map_md_chars_over_budget")

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(text, encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_REPORT.write_text(md, encoding="utf-8")
    _write_mdc(doc)
    print(f"WROTE: {OUT_JSON}")
    print(f"WROTE: {MDC}")
    print(f"OK={doc['ok']} coords={doc['coord_count']} md_chars={doc['map_md_chars']}")
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
