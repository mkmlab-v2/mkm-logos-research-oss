#!/usr/bin/env python3
"""Build bounded_lane_pin_v1 JSON from resume pack + MISSION_LOG lane row.

Auto-generates thin per-lane pins for run_bounded_lane_loop_v1.py (shadow only).

  py scripts/build_bounded_lane_pin_from_resume_pack_v1.py --lane infra
  py scripts/build_bounded_lane_pin_from_resume_pack_v1.py --lane ms --refresh-resume-pack

Output: docs/final/artifacts/bounded_lane_pin_{lane}_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PIN_SCHEMA = ROOT / "docs/final/schemas/bounded_lane_pin_v1.schema.json"
RESUME_PACK = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
MISSION_LOG = ROOT / "MISSION_LOG.md"
INDEX_PATH = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
GRAPH_PATH = ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json"

# Primary LTM graph concept per bounded pin lane (single hint — graph 통째 주입 금지).
LANE_LTM_PRIMARY_CONCEPT: dict[str, str] = {
    "ms": "ms_lane_submission_hold",
    "oracle": "prophecy_research_only_boundary",
    "infra": "infra_solo_scheduler_stack",
    "design": "design_showroom_domain_portfolio",
    "ops": "lane_resume_pack_contract",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    LANE_OPS_PACKS,
    extract_node_from_index,
)

DEFAULT_FORBIDDEN = [
    "track_a_promote",
    "live_trade",
    "todo_queue_enqueue",
    "cursor_infinite_chat",
]

FIXTURE_LANES = ("ms", "oracle", "infra", "design")

A2A_PEER_BRIEF_LANES = frozenset({"ms", "oracle", "infra"})

LANE_PIN_CONFIG: dict[str, dict[str, Any]] = {
    "ms": {
        "node_id": "prism_ops_lane_ms",
        "row_re": re.compile(r"\|\s*\*\*MS\*\*\s*\|\s*(.+?)\s*\|"),
    },
    "oracle": {
        "node_id": "prism_ops_lane_oracle",
        "row_re": re.compile(r"\|\s*\*\*Oracle·예언·align-panel\*\*\s*\|\s*(.+?)\s*\|"),
    },
    "infra": {
        "node_id": "prism_ops_lane_infra",
        "row_re": re.compile(r"\|\s*\*\*Infra/GPU\*\*\s*\|\s*(.+?)\s*\|"),
    },
    "design": {
        "node_id": None,
        "row_re": re.compile(r"\|\s*\*\*Design/Showroom\*\*\s*\|\s*(.+?)\s*\|"),
    },
    "ops": {
        "node_id": None,
        "row_re": re.compile(r"\|\s*\*\*Ops Memory AI↔AI\*\*\s*\|\s*(.+?)\s*\|"),
    },
}

FALLBACK_ACTION = "Refresh resume pack then P0 gate path verify (bounded loop default)."


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_action(text: str) -> str:
    cleaned = re.sub(r"\*\*", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 240:
        cleaned = cleaned[:237].rstrip() + "..."
    return cleaned or FALLBACK_ACTION


def _parse_table_action_cell(block: str) -> str:
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 2 and parts[1]:
            return _clean_action(parts[1])
    return ""


def _extract_from_mission_log_row(root: Path, lane: str) -> str:
    cfg = LANE_PIN_CONFIG[lane]
    if not MISSION_LOG.is_file():
        return ""
    text = MISSION_LOG.read_text(encoding="utf-8")
    row_re = cfg.get("row_re")
    if row_re:
        match = row_re.search(text)
        if match:
            return _clean_action(match.group(1))
    return ""


def _extract_from_ops_index(root: Path, lane: str) -> str:
    cfg = LANE_PIN_CONFIG[lane]
    node_id = cfg.get("node_id")
    if not node_id or not INDEX_PATH.is_file():
        return ""
    index = _load_json(INDEX_PATH)
    nodes = index.get("nodes") or {}
    node = nodes.get(node_id)
    if not isinstance(node, dict):
        return ""
    try:
        block = extract_node_from_index(root, node)
    except (FileNotFoundError, ValueError):
        return ""
    return _parse_table_action_cell(block)


def _extract_from_resume_pack_pins(resume_pack: dict[str, Any], lane: str) -> str:
    cfg = LANE_PIN_CONFIG[lane]
    node_id = cfg.get("node_id")
    pins = resume_pack.get("ops_memory_pins") or []
    for pin in pins:
        if not isinstance(pin, dict):
            continue
        if node_id and pin.get("node_id") == node_id:
            preview = pin.get("slice_preview") or ""
            action = _parse_table_action_cell(preview)
            if action:
                return action
    next_one = next(
        (p for p in pins if isinstance(p, dict) and p.get("node_id") == "prism_ops_mission_log_next_one"),
        None,
    )
    if next_one:
        preview = next_one.get("slice_preview") or ""
        row_re = cfg.get("row_re")
        if row_re and preview:
            match = row_re.search(preview)
            if match:
                return _clean_action(match.group(1))
    return ""


def extract_next_action_one_line(
    root: Path,
    lane: str,
    *,
    resume_pack: dict[str, Any] | None = None,
) -> str:
    for extractor in (
        lambda: _extract_from_mission_log_row(root, lane),
        lambda: _extract_from_ops_index(root, lane),
        lambda: _extract_from_resume_pack_pins(resume_pack or {}, lane)
        if resume_pack
        else "",
    ):
        action = extractor()
        if action:
            return action
    return FALLBACK_ACTION


def _resume_pack_argv(lane: str) -> list[str]:
    argv = ["scripts/build_mkm_chat_resume_pack_v1.py"]
    if lane in LANE_OPS_PACKS:
        argv.extend(["--lane", lane])
    return argv


def _peer_handoff_pointer(root: Path, lane: str) -> str | None:
    if lane not in A2A_PEER_BRIEF_LANES:
        return None
    brief = (
        root
        / f"docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
    )
    if not brief.is_file():
        return None
    return brief.relative_to(root).as_posix()


def resolve_ltm_hint(root: Path, lane: str) -> dict[str, Any] | None:
    """Single graph concept coordinate for multi-file edit routing ([HYPO] B-track)."""
    concept_id = LANE_LTM_PRIMARY_CONCEPT.get(lane)
    if not concept_id or not GRAPH_PATH.is_file():
        return None
    graph = _load_json(GRAPH_PATH)
    concepts = graph.get("concepts") or {}
    concept = concepts.get(concept_id)
    if not isinstance(concept, dict):
        return None
    topo = concept.get("topology") or {}
    hint: dict[str, Any] = {"concept_id": concept_id}
    layer = topo.get("software_layer")
    if isinstance(layer, str) and layer.strip():
        hint["software_layer"] = layer.strip()
    radius = topo.get("blast_radius")
    if isinstance(radius, str) and radius.strip():
        hint["blast_radius"] = radius.strip()
    label = concept.get("label_ko")
    if isinstance(label, str) and label.strip():
        hint["label_ko"] = label.strip()[:160]
    return hint


def build_pin(
    root: Path,
    lane: str,
    *,
    resume_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    next_action = extract_next_action_one_line(root, lane, resume_pack=resume_pack)
    pin: dict[str, Any] = {
        "schema": "bounded_lane_pin_v1",
        "generated_at_utc": _utc(),
        "lane": lane,
        "next_action_one_line": next_action,
        "fact_lock_pointer": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
        "forbidden": list(DEFAULT_FORBIDDEN),
        "max_steps_per_loop": 2,
        "max_wall_seconds_per_loop": 600,
        "steps": [
            {
                "step_id": "resume_pack",
                "runner": "python",
                "argv": _resume_pack_argv(lane),
            },
            {
                "step_id": "p0_gate_paths",
                "runner": "powershell",
                "argv": ["scripts/verify_p0_constitution_gate_paths.ps1"],
            },
        ],
    }
    peer = _peer_handoff_pointer(root, lane)
    if peer:
        pin["peer_handoff_pointer"] = peer
    ltm_hint = resolve_ltm_hint(root, lane)
    if ltm_hint:
        pin["ltm_hint"] = ltm_hint
    return pin


def write_lane_fixtures(root: Path, *, resume_pack: dict[str, Any] | None = None) -> list[Path]:
    fixture_dir = root / "docs/final/artifacts/fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for lane in FIXTURE_LANES:
        pin = build_pin(root, lane, resume_pack=resume_pack)
        errors = validate_pin(pin)
        if errors:
            raise ValueError(f"fixture pin invalid for {lane}: {errors}")
        out = fixture_dir / f"bounded_lane_pin_{lane}_v1.example.json"
        out.write_text(json.dumps(pin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out)
    return written


def validate_pin(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "bounded_lane_pin_v1":
        errors.append("schema must be bounded_lane_pin_v1")
    for key in ("lane", "next_action_one_line", "forbidden", "steps"):
        if key not in doc:
            errors.append(f"missing required field: {key}")
    if PIN_SCHEMA.is_file():
        try:
            import jsonschema

            schema = _load_json(PIN_SCHEMA)
            jsonschema.validate(doc, schema)
        except ImportError:
            pass
        except jsonschema.ValidationError as exc:
            errors.append(f"jsonschema: {exc.message}")
    return errors


def _refresh_resume_pack(root: Path, lane: str) -> int:
    cmd = [sys.executable, *_resume_pack_argv(lane)]
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--lane",
        choices=sorted(LANE_PIN_CONFIG),
        default="infra",
        help="Target lane for bounded pin (default: infra).",
    )
    ap.add_argument(
        "--refresh-resume-pack",
        action="store_true",
        help="Run build_mkm_chat_resume_pack_v1.py before reading pins.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: docs/final/artifacts/bounded_lane_pin_{lane}_latest.json).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print pin JSON without writing.")
    ap.add_argument(
        "--write-fixtures",
        action="store_true",
        help="Write docs/final/artifacts/fixtures/bounded_lane_pin_{ms,oracle,infra,design}_v1.example.json",
    )
    args = ap.parse_args()

    resume_pack: dict[str, Any] | None = None
    if RESUME_PACK.is_file():
        resume_pack = _load_json(RESUME_PACK)

    if args.write_fixtures:
        try:
            paths = write_lane_fixtures(ROOT, resume_pack=resume_pack)
        except ValueError as exc:
            print(f"build_bounded_lane_pin: {exc}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "ok": True,
                    "fixtures": [p.relative_to(ROOT).as_posix() for p in paths],
                    "reproduce": "py scripts/build_bounded_lane_pin_from_resume_pack_v1.py --write-fixtures",
                },
                ensure_ascii=False,
            )
        )
        return 0

    lane = args.lane.strip().lower()
    out_path = args.out
    if out_path is None:
        out_path = ROOT / f"docs/final/artifacts/bounded_lane_pin_{lane}_latest.json"
    elif not out_path.is_absolute():
        out_path = ROOT / out_path

    if args.refresh_resume_pack:
        rc = _refresh_resume_pack(ROOT, lane)
        if rc != 0:
            print(f"build_bounded_lane_pin: resume pack refresh failed exit {rc}", file=sys.stderr)
            return rc
        resume_pack = _load_json(RESUME_PACK) if RESUME_PACK.is_file() else None

    pin = build_pin(ROOT, lane, resume_pack=resume_pack)
    errors = validate_pin(pin)
    if errors:
        print(f"build_bounded_lane_pin: pin validation failed: {errors}", file=sys.stderr)
        return 2

    payload = json.dumps(pin, indent=2, ensure_ascii=False) + "\n"
    if args.dry_run:
        print(payload, end="")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    rel = out_path.relative_to(ROOT).as_posix()
    print(
        json.dumps(
            {
                "ok": True,
                "lane": lane,
                "out": rel,
                "next_action_one_line": pin["next_action_one_line"],
                "reproduce": f"py scripts/build_bounded_lane_pin_from_resume_pack_v1.py --lane {lane}",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
