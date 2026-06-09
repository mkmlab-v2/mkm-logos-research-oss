"""Multi-resolution todo index — MISSION_LOG + CENTRAL + delegation + audit ([HYPO]).

B-track / research_only — todo_queue auto-enqueue forbidden.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECTION_RE = re.compile(r"^###\s+(.+)$")
NEXT_ACTION_RE = re.compile(
    r"^\*\*(?:레인 다음 1타|post-340 다음 1타|글로벌 다음 1타|Next-Gen 다음 1타|Hangul v2 다음 1타)(?:\s*\(human\))?:\*\*\s*(.+)$"
)
CHECKPOINT_LINE_RE = re.compile(
    r"^-\s+\*\*(\d{4}-\d{2}-\d{2}T[\d:.]+Z)\*\*\s+—\s+(.+)$"
)

DELEGATION_MAPS = (
    "reports/delegation_multi_res_index_approval_map_v1_latest.json",
    "reports/delegation_ai_to_ai_governance_approval_map_v1_latest.json",
    "reports/delegation_nextgen_engine_approval_map_v1_latest.json",
)

INTERESTING_DECISIONS = frozenset(
    {
        "failed",
        "verification_incomplete",
        "chain_failed",
        "reject",
        "hold",
        "meta_layer_envelope_v1",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _slug_lane(section_title: str) -> str:
    t = section_title.strip()
    t = re.sub(r"[`\[\]()]|[^\w\s가-힣·/]", "", t)
    t = re.sub(r"\s+", "_", t)[:48]
    return t or "unknown_lane"


def parse_mission_log_lane_actions(mission_log_text: str) -> list[dict[str, Any]]:
    lines = mission_log_text.splitlines()
    current_section = "board_top"
    actions: list[dict[str, Any]] = []
    priority = 10

    for line in lines:
        sec = SECTION_RE.match(line)
        if sec:
            current_section = sec.group(1).strip()
            continue
        m = NEXT_ACTION_RE.match(line.strip())
        if not m:
            continue
        essence = m.group(1).strip()
        lane_key = _slug_lane(current_section)
        human_only = "(human)" in line or "human" in essence.lower()[:40]
        action_id = f"lane_{lane_key}_{len(actions)}"
        actions.append(
            {
                "action_id": action_id,
                "lane_key": lane_key,
                "essence": essence[:500],
                "priority": max(1, priority),
                "source_section": current_section[:120],
                "human_only": human_only,
            }
        )
        priority = max(1, priority - 1)

    # Cursor 3층 post-340 row gets explicit boost if present
    for row in actions:
        if "build_multi_res_todo_index" in row.get("essence", ""):
            row["priority"] = 10
            row["lane_key"] = "cursor_3layer_todo"

    actions.sort(key=lambda r: (-int(r["priority"]), r["action_id"]))
    return actions


def parse_central_checkpoints(central_text: str, *, max_rows: int = 8) -> list[dict[str, Any]]:
    start = central_text.find("<!-- ATHENA_CHECKPOINT_V1_START -->")
    end = central_text.find("<!-- ATHENA_CHECKPOINT_V1_END -->")
    if start < 0 or end < 0 or end <= start:
        return []
    block = central_text[start:end]
    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        m = CHECKPOINT_LINE_RE.match(line.strip())
        if not m:
            continue
        ts, essence = m.group(1), m.group(2).strip()
        rows.append(
            {
                "checkpoint_id": f"ckpt_{ts.replace(':', '').replace('-', '')}",
                "timestamp_utc": ts,
                "essence": essence[:400],
            }
        )
    return rows[:max_rows]


def collect_delegation_pending(root: Path) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for rel in DELEGATION_MAPS:
        path = root / rel
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        map_key = rel.split("/")[-1].replace("_latest.json", "")
        for node in doc.get("nodes") or []:
            status = node.get("status")
            approval = node.get("approval")
            if status in ("done", "skipped") and approval != "REVIEW":
                continue
            if approval == "STOP" and status == "skipped":
                continue
            pending.append(
                {
                    "node_id": node.get("id", "?"),
                    "map_key": map_key,
                    "status": status or "unknown",
                    "approval": approval or "unknown",
                    "evidence": node.get("evidence"),
                    "name": node.get("name"),
                }
            )
    return pending


def collect_audit_tail(root: Path, *, max_rows: int = 15) -> list[dict[str, Any]]:
    log_path = root / "reports/agent_decisions_log.jsonl"
    if not log_path.is_file():
        return []
    lines = log_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    tail: list[dict[str, Any]] = []
    for raw in reversed(lines[-200:]):
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        decision = str(row.get("decision", ""))
        if decision not in INTERESTING_DECISIONS and "fail" not in decision.lower():
            if len(tail) >= max_rows // 2:
                continue
        tail.append(
            {
                "timestamp": row.get("timestamp", ""),
                "mission_id": row.get("mission_id", ""),
                "decision": decision,
                "evidence_path": row.get("evidence_path", ""),
                "stage": row.get("stage", ""),
            }
        )
        if len(tail) >= max_rows:
            break
    tail.reverse()
    return tail


def build_high_res_pointers(root: Path) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = [
        {
            "pointer_id": "ptr_mission_log",
            "file_path": "MISSION_LOG.md",
            "anchor_hint": "## 🚀 전술 작전 보드",
        },
        {
            "pointer_id": "ptr_central_checkpoint",
            "file_path": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "anchor_hint": "<!-- ATHENA_CHECKPOINT_V1_START -->",
        },
        {
            "pointer_id": "ptr_agent_decisions",
            "file_path": "reports/agent_decisions_log.jsonl",
        },
        {
            "pointer_id": "ptr_ops_memory_index",
            "file_path": "storage/meta/mkm_ops_memory_index_v1.json",
        },
        {
            "pointer_id": "ptr_multi_res_fusion_bench",
            "file_path": "reports/multi_res_fusion_bench_v1_latest.json",
        },
    ]
    ops_idx = root / "storage/meta/mkm_ops_memory_index_v1.json"
    if ops_idx.is_file():
        doc = json.loads(ops_idx.read_text(encoding="utf-8-sig"))
        for node_id in list((doc.get("nodes") or {}).keys())[:6]:
            pointers.append(
                {
                    "pointer_id": f"ptr_ops_{node_id}",
                    "file_path": "storage/meta/mkm_ops_memory_index_v1.json",
                    "node_id": node_id,
                }
            )
    return pointers


def build_coordinate_map(
    lane_actions: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    coords: list[dict[str, Any]] = []
    ptr_cursor = "ptr_mission_log"
    ptr_central = "ptr_central_checkpoint"
    ckpt0 = checkpoints[0]["checkpoint_id"] if checkpoints else None

    for i, action in enumerate(lane_actions[:12]):
        low_id = action["action_id"]
        mid_id = ckpt0 if i == 0 and ckpt0 else (checkpoints[i % len(checkpoints)]["checkpoint_id"] if checkpoints else None)
        high_id = ptr_cursor if i % 2 == 0 else ptr_central
        coords.append(
            {
                "coord_id": f"coord_{i}",
                "low_id": low_id,
                "mid_id": mid_id,
                "high_id": high_id,
                "resolution_tier": "L-M-H" if mid_id else "L-H",
            }
        )

    if lane_actions and pointers:
        top = lane_actions[0]
        coords.insert(
            0,
            {
                "coord_id": "coord_primary_post_340",
                "low_id": top["action_id"],
                "mid_id": ckpt0,
                "high_id": "ptr_ops_memory_index",
                "resolution_tier": "L-M-H",
            },
        )
    return coords


def build_todo_index_document(root: Path, *, generated_at_utc: str | None = None) -> dict[str, Any]:
    sources_present: list[str] = []
    mission_log = root / "MISSION_LOG.md"
    central = root / "docs/final/CENTRAL_AGENT_MEMORY_V1.md"

    lane_actions: list[dict[str, Any]] = []
    if mission_log.is_file():
        lane_actions = parse_mission_log_lane_actions(
            mission_log.read_text(encoding="utf-8-sig", errors="replace")
        )
        sources_present.append("MISSION_LOG.md")

    checkpoints: list[dict[str, Any]] = []
    if central.is_file():
        checkpoints = parse_central_checkpoints(
            central.read_text(encoding="utf-8-sig", errors="replace")
        )
        sources_present.append("docs/final/CENTRAL_AGENT_MEMORY_V1.md")

    delegation_pending = collect_delegation_pending(root)
    if delegation_pending:
        sources_present.append("reports/delegation_*_approval_map_v1_latest.json")

    audit_tail = collect_audit_tail(root)
    if audit_tail:
        sources_present.append("reports/agent_decisions_log.jsonl")

    pointers = build_high_res_pointers(root)
    ops_linked = (root / "storage/meta/mkm_ops_memory_index_v1.json").is_file()
    fusion_linked = (root / "reports/multi_res_fusion_bench_v1_latest.json").is_file()
    if ops_linked:
        sources_present.append("storage/meta/mkm_ops_memory_index_v1.json")
    if fusion_linked:
        sources_present.append("reports/multi_res_fusion_bench_v1_latest.json")

    coordinate_map = build_coordinate_map(lane_actions, checkpoints, pointers)

    return {
        "schema": "multi_res_todo_index_v1",
        "generated_at_utc": generated_at_utc or _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] todo coordinate index — To-Do complete ≠ Track A·live·MISSION promotion; "
            "todo_queue auto-enqueue forbidden"
        ),
        "todo_queue_auto_enqueue": False,
        "meta": {
            "sources_present": sources_present,
            "n_low_res": len(lane_actions),
            "n_mid_res": len(checkpoints) + len(delegation_pending),
            "n_high_res": len(pointers) + len(audit_tail),
            "ops_memory_index_linked": ops_linked,
            "fusion_bench_linked": fusion_linked,
        },
        "low_res": {"lane_actions": lane_actions},
        "mid_res": {
            "checkpoints": checkpoints,
            "delegation_pending": delegation_pending,
        },
        "high_res": {
            "pointers": pointers,
            "audit_tail": audit_tail,
        },
        "coordinate_map": coordinate_map,
        "harness_refs": {
            "harness_1_state_externalization": (
                "[HYPO] disk pointers + lane essence — policy decides, harness holds state"
            ),
            "moss_evidence_replay_gate": (
                "[HYPO] audit_tail + delegation_pending — replay via exit0/pytest; "
                "no alwaysApply self-modify (global_stop)"
            ),
            "adacom_context_manager": (
                "[HYPO] lane-filtered inject via ops memory resume pack — agent frozen"
            ),
        },
    }
