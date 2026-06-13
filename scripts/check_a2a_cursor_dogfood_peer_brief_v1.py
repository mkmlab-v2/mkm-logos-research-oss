#!/usr/bin/env python3
"""Cursor dogfood peer-brief smoke — automated stand-in for parallel-chat handoff checklist.

[HYPO] Validates lane brief artifacts + expand J floor. Human still confirms peer chat UX.

  py scripts/check_a2a_cursor_dogfood_peer_brief_v1.py
  py scripts/check_a2a_cursor_dogfood_peer_brief_v1.py --strict-exit
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_a2a_tier3_cursor_wire_handoff_pilot_v1 import (  # noqa: E402
    JACCARD_ADAPT_FLOOR,
    LANE_JACCARD_ADAPT_FLOOR,
    lane_artifact_paths,
)
from mkm_ops_memory_index_lib_v1 import LANE_OPS_PACKS  # noqa: E402

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_cursor_dogfood_peer_check_v1_latest.json"
DEFAULT_MD = ROOT / "docs/final/artifacts/a2a_cursor_dogfood_peer_check_v1_latest.md"
REQUIRED_BRIEF_BOUNDARY_MARKERS = (
    "SEND_GATE: HOLD",
)


def _brief_has_fail_comp_marker(text: str) -> bool:
    return "FAIL-COMP-004" in text or "FAIL COMP 004" in text


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_check(root: Path) -> dict[str, Any]:
    lanes: dict[str, Any] = {}
    failures: list[str] = []
    human_steps: list[str] = []

    for lane in sorted(LANE_OPS_PACKS.keys()):
        paths = lane_artifact_paths(root, lane)
        pilot = _read_json(paths["pilot"])
        brief_path = paths["brief"]
        brief_text = brief_path.read_text(encoding="utf-8") if brief_path.is_file() else ""
        kpi = pilot.get("kpi_headline") or {}
        j = kpi.get("expand_jaccard")
        floor = LANE_JACCARD_ADAPT_FLOOR.get(lane, JACCARD_ADAPT_FLOOR)
        row: dict[str, Any] = {
            "pilot_ok": pilot.get("pilot_ok"),
            "brief_exists": brief_path.is_file(),
            "expand_jaccard": j,
            "jaccard_adapt_floor": floor,
            "brief_artifact": paths["brief"].relative_to(root).as_posix(),
        }
        if not pilot.get("pilot_ok"):
            failures.append(f"{lane}: pilot_ok false")
        if not brief_path.is_file():
            failures.append(f"{lane}: brief missing")
        else:
            for marker in ("mkm_chat_resume_pack_latest.md", "[HYPO]"):
                if marker not in brief_text:
                    failures.append(f"{lane}: brief missing marker {marker!r}")
            for marker in REQUIRED_BRIEF_BOUNDARY_MARKERS:
                if marker not in brief_text:
                    failures.append(f"{lane}: brief missing boundary {marker!r}")
            if not _brief_has_fail_comp_marker(brief_text):
                failures.append(f"{lane}: brief missing FAIL-COMP-004 marker")
        if j is None or float(j) < floor:
            failures.append(f"{lane}: expand_jaccard below {floor}")
        expanded = ((pilot.get("peer_receive") or {}).get("expanded_text_preview")) or ""
        if expanded and "SEND_GATE" not in expanded:
            failures.append(f"{lane}: expanded preview missing SEND_GATE")
        lanes[lane] = row
        human_steps.append(
            f"Peer chat `{lane}`: @docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
        )

    index = _read_json(root / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json")
    if int(index.get("lane_count") or 0) < len(LANE_OPS_PACKS):
        failures.append("lane_index incomplete")

    check_ok = not failures
    return {
        "schema": "a2a_cursor_dogfood_peer_check_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "check_ok": check_ok,
        "jaccard_floor": JACCARD_ADAPT_FLOOR,
        "failures": failures,
        "lanes": lanes,
        "human_parallel_chat_checklist": [
            "Source chat: @docs/final/artifacts/mkm_chat_resume_pack_latest.md (unchanged)",
            *human_steps,
            "Confirm peer agent cites SEND_GATE: HOLD without MISSION_LOG full paste",
            "Confirm no Track A 47% merged into A2A headline in peer reply",
        ],
        "repro_command": "py scripts/check_a2a_cursor_dogfood_peer_brief_v1.py --strict-exit",
    }


def render_md(doc: dict[str, Any]) -> str:
    failures = doc.get("failures") or []
    checklist = doc.get("human_parallel_chat_checklist") or []
    lines = [
        "# A2A Cursor dogfood — peer brief check [HYPO]",
        "",
        f"- generated: `{doc.get('generated_at_utc')}`",
        f"- check_ok: `{doc.get('check_ok')}`",
        f"- jaccard_floor: `{doc.get('jaccard_floor')}`",
        "",
        "## Automated",
        "",
        f"- failures: {failures if failures else 'none'}",
        "",
        "## Human parallel-chat checklist",
        "",
    ]
    for step in checklist:
        lines.append(f"- {step}")
    lines.extend(["", "SEND_GATE: HOLD · B-track only."])
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    doc = build_check(ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.md_out}")
    print(f"check_ok={doc.get('check_ok')} failures={doc.get('failures')}")
    if args.strict_exit and not doc.get("check_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
