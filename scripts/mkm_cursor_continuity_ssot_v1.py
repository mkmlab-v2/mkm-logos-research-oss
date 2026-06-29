"""MKM Cursor continuity — required SSOT refs (MISSION_LOG · 장기기억 · LTM)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Paths that must appear in envelope deep_fetch or turn meta — never omit on resume.
REQUIRED_SSOT_REFS: tuple[dict[str, str], ...] = (
    {
        "id": "mission_log",
        "path": "MISSION_LOG.md",
        "role": "ops_board_next_one_pin_only",
    },
    {
        "id": "central_memory",
        "path": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        "role": "checkpoint_block",
    },
    {
        "id": "resume_pack_md",
        "path": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
        "role": "L1_shallow_inject",
    },
    {
        "id": "resume_pack_json",
        "path": "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
        "role": "L1_machine",
    },
    {
        "id": "deep_handoff_envelope",
        "path": "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json",
        "role": "L2_handoff_wire",
    },
    {
        "id": "ltm_graph",
        "path": "storage/meta/mkm_long_term_memory_graph_v1.json",
        "role": "LTM_graph_os",
    },
    {
        "id": "ops_memory_index",
        "path": "storage/meta/mkm_ops_memory_index_v1.json",
        "role": "ops_memory_index",
    },
    {
        "id": "commander_resume_triggers",
        "path": "docs/final/artifacts/mkm_commander_resume_triggers_v1.json",
        "role": "resume_triggers_ssot",
    },
    {
        "id": "meta_cognition_roadmap",
        "path": "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "role": "phase_roadmap",
    },
    {
        "id": "turn_meta_log",
        "path": "reports/mkm_cursor_turn_meta_log.jsonl",
        "role": "turn_audit_log",
    },
)

REQUIRED_PATH_STRINGS: tuple[str, ...] = tuple(
    ref["path"] for ref in REQUIRED_SSOT_REFS if ref["id"] != "turn_meta_log"
)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def missing_required_paths(paths: list[str], *, extra: list[str] | None = None) -> list[str]:
    pool = [normalize_path(p).lower() for p in (paths + (extra or []))]
    missing: list[str] = []
    for ref in REQUIRED_SSOT_REFS:
        if ref["id"] == "turn_meta_log":
            continue
        p = ref["path"].lower()
        if not any(item == p or p in item for item in pool):
            missing.append(ref["path"])
    return missing


def required_ssot_refs_payload() -> list[dict[str, str]]:
    return [dict(ref) for ref in REQUIRED_SSOT_REFS]


def merge_deep_fetch_queue(
    previous: list[str] | None,
    current: list[str] | None,
    *,
    limit: int = 12,
) -> list[str]:
    """Preserve prior deep_fetch_next items when continuity_id continues."""
    seen: set[str] = set()
    out: list[str] = []
    for seq in (previous or [], REQUIRED_PATH_STRINGS, current or []):
        for raw in seq:
            p = normalize_path(str(raw))
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
            if len(out) >= limit:
                return out
    return out


def read_jsonl_tail(path: Path, *, continuity_id: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            import json

            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(doc.get("continuity_id") or "") == continuity_id:
            last = doc
    return last


def verify_required_files_exist(root: Path | None = None) -> list[str]:
    base = root or ROOT
    missing: list[str] = []
    for ref in REQUIRED_SSOT_REFS:
        if ref["id"] == "turn_meta_log":
            continue
        p = base / ref["path"]
        if not p.is_file():
            missing.append(ref["path"])
    return missing
