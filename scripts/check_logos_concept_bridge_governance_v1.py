#!/usr/bin/env python3
"""Phase 2 gate: concept_bridge LLM layer + human_reviewed ratio ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
DEFAULT_LLM_PLAN = ROOT / "docs/final/artifacts/logos_concept_bridge_llm_plan_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_concept_bridge_governance_v1_latest.json"

LLM_METHOD_MARKERS = ("gemini", "llm", "batch")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_llm_generation(method: str) -> bool:
    m = (method or "").lower()
    return any(marker in m for marker in LLM_METHOD_MARKERS)


def check(
    *,
    registry: dict[str, Any],
    llm_plan: dict[str, Any] | None,
    min_human_reviewed_ratio: float,
    min_human_reviewed_count: int,
    min_llm_bridge_count: int,
    min_bridge_count: int,
) -> dict[str, Any]:
    entries = [e for e in registry.get("entries") or [] if isinstance(e, dict) and e.get("present")]
    bridge_count = len(entries)
    human_reviewed_count = sum(1 for e in entries if e.get("human_reviewed"))
    llm_entries = [e for e in entries if _is_llm_generation(str(e.get("generation_method") or ""))]
    llm_bridge_count = len(llm_entries)
    ratio = (human_reviewed_count / bridge_count) if bridge_count else 0.0
    governance_warning_zero_human = bool(registry.get("governance_warning_zero_human"))

    gate_failures: list[str] = []
    if bridge_count < min_bridge_count:
        gate_failures.append(f"bridge_count {bridge_count} < min_bridge_count {min_bridge_count}")
    if human_reviewed_count < min_human_reviewed_count:
        gate_failures.append(
            f"human_reviewed_count {human_reviewed_count} < min {min_human_reviewed_count}"
        )
    if ratio < min_human_reviewed_ratio:
        gate_failures.append(
            f"human_reviewed_ratio {ratio:.4f} < min {min_human_reviewed_ratio}"
        )
    if governance_warning_zero_human:
        gate_failures.append("governance_warning_zero_human")
    if llm_bridge_count < min_llm_bridge_count:
        gate_failures.append(f"llm_bridge_count {llm_bridge_count} < min {min_llm_bridge_count}")
    if not llm_plan:
        gate_failures.append("llm_plan_missing")

    unsigned = [
        {
            "concept_id": e.get("concept_id"),
            "artifact_path": e.get("artifact_path"),
            "generation_method": e.get("generation_method"),
        }
        for e in entries
        if not e.get("human_reviewed")
    ]

    return {
        "schema": "logos_concept_bridge_governance_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "bridge_count": bridge_count,
        "human_reviewed_count": human_reviewed_count,
        "human_reviewed_ratio": round(ratio, 4),
        "governance_warning_zero_human": governance_warning_zero_human,
        "llm_bridge_count": llm_bridge_count,
        "llm_plan_present": llm_plan is not None,
        "unsigned_bridge_sample": unsigned[:16],
        "unsigned_bridge_count": len(unsigned),
        "gate_pass": len(gate_failures) == 0,
        "gate_failures": gate_failures,
        "thresholds": {
            "min_bridge_count": min_bridge_count,
            "min_human_reviewed_count": min_human_reviewed_count,
            "min_human_reviewed_ratio": min_human_reviewed_ratio,
            "min_llm_bridge_count": min_llm_bridge_count,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--llm-plan-json", type=Path, default=DEFAULT_LLM_PLAN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-human-reviewed-ratio", type=float, default=0.5)
    ap.add_argument("--min-human-reviewed-count", type=int, default=1)
    ap.add_argument("--min-llm-bridge-count", type=int, default=1)
    ap.add_argument("--min-bridge-count", type=int, default=5)
    args = ap.parse_args()

    if not args.registry_json.is_file():
        print(json.dumps({"ok": False, "error": "registry_missing"}))
        return 2

    registry = json.loads(args.registry_json.read_text(encoding="utf-8-sig"))
    llm_plan = None
    if args.llm_plan_json.is_file():
        llm_plan = json.loads(args.llm_plan_json.read_text(encoding="utf-8-sig"))

    doc = check(
        registry=registry,
        llm_plan=llm_plan,
        min_human_reviewed_ratio=args.min_human_reviewed_ratio,
        min_human_reviewed_count=args.min_human_reviewed_count,
        min_llm_bridge_count=args.min_llm_bridge_count,
        min_bridge_count=args.min_bridge_count,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["gate_pass"],
                "human_reviewed_ratio": doc["human_reviewed_ratio"],
                "llm_bridge_count": doc["llm_bridge_count"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
