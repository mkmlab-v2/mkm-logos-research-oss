#!/usr/bin/env python3
"""Build Human Gate queue for concept_bridge artifacts lacking signoff ([HYPO]).

Reads registry + LLM plan; lists present bridges without human_signoff marker.

Reproducible:
  py scripts/build_logos_concept_bridge_human_gate_queue_v1.py --wave 1
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
LLM_PLAN = ROOT / "docs/final/artifacts/logos_concept_bridge_llm_plan_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_human_gate_queue_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_signoff_marker(artifact_path: Path) -> bool:
    if not artifact_path.is_file():
        return False
    doc = _read_json(artifact_path)
    policy = doc.get("policy") if isinstance(doc.get("policy"), dict) else {}
    return bool(policy.get("human_signoff_completed") or policy.get("human_reviewed"))


def _rel_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_queue(
    *,
    registry_path: Path = REGISTRY,
    llm_plan_path: Path = LLM_PLAN,
    wave: int = 1,
) -> dict[str, Any]:
    generated_at_utc = _utc_now()
    reg = _read_json(registry_path) if registry_path.is_file() else {}
    plan = _read_json(llm_plan_path) if llm_plan_path.is_file() else {}

    entries: list[dict[str, Any]] = []
    slot = 1
    for reg_entry in reg.get("entries") or []:
        if not isinstance(reg_entry, dict) or not reg_entry.get("present"):
            continue
        rel = reg_entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        artifact_path = ROOT / rel
        signed = _has_signoff_marker(artifact_path)
        if signed or reg_entry.get("human_reviewed"):
            continue
        concept_id = reg_entry.get("concept_id") or ""
        entries.append(
            {
                "slot_id": f"bridge_{slot:03d}",
                "slot_num": slot,
                "status": "human_gate_pending",
                "wave": wave,
                "concept_id": concept_id,
                "label_ko": reg_entry.get("label_ko"),
                "artifact_path": rel,
                "path_count": reg_entry.get("path_count"),
                "generation_method": reg_entry.get("generation_method"),
                "signoff_marker_present": False,
                "human_review_required": True,
                "source": "concept_bridge_registry_v1",
                "nl_reference_only": True,
            }
        )
        slot += 1

    governance = plan.get("governance") if isinstance(plan.get("governance"), dict) else {}
    present_n = len([e for e in reg.get("entries") or [] if isinstance(e, dict) and e.get("present")])

    return {
        "schema": "logos_concept_bridge_human_gate_queue_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "send_gate": "HOLD",
        "wave": wave,
        "queue_count": len(entries),
        "registry_bridge_count": present_n,
        "registry_human_reviewed_count": reg.get("human_reviewed_count"),
        "registry_path": _rel_path(registry_path),
        "llm_plan_path": _rel_path(llm_plan_path),
        "llm_plan_governance": governance,
        "merge_policy": (
            "human_gate: commander ACCEPT → mark_logos_concept_bridge_human_signoff_v1 "
            "(B-track ack only; not Track A promotion)"
        ),
        "entries": entries,
        "reproducible_command": "py scripts/build_logos_concept_bridge_human_gate_queue_v1.py --wave 1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--llm-plan", type=Path, default=LLM_PLAN)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--wave", type=int, default=1)
    args = parser.parse_args()

    if not args.registry.is_file():
        print(f"Missing registry: {args.registry}", file=sys.stderr)
        return 2

    doc = build_queue(
        registry_path=args.registry,
        llm_plan_path=args.llm_plan,
        wave=args.wave,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  wave={args.wave} pending={doc['queue_count']} registry_present={doc['registry_bridge_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
