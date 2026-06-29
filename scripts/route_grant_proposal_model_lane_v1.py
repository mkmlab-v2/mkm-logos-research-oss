#!/usr/bin/env python3
"""Grant / government proposal draft task → model lane router (dry-run v0).

Maps OpenData 327 / open-innovation proposal *draft* steps to tier_cheap,
tier_premium, script_only, or human_only. No LLM API calls in v0 — metering log only.

research_only · HWPX/PMS auto-submit forbidden (see MISSION_LOG backlog row).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "tests/fixtures/grant_proposal_router_tasks_v1.example.jsonl"
DEFAULT_OUT = ROOT / "reports/grant_proposal_model_route_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/grant_proposal_model_route_v1.jsonl"

SCHEMA = "grant_proposal_model_route_v1"
RESEARCH_ONLY = True

# task_kind → (lane_id, model_tier, model_slot_hint, invoke_llm)
LANE_MAP: dict[str, tuple[str, str, str, bool]] = {
    "outline": ("L0", "tier_cheap", "moe_bus", True),
    "table_fill": ("L0", "tier_cheap", "moe_bus", True),
    "grep_evidence": ("L0", "script_only", "constitution_grep", False),
    "json_field_copy": ("L0", "script_only", "local_ssot", False),
    "narrative_section": ("L1", "tier_premium", "premium_reasoning", True),
    "business_model": ("L1", "tier_premium", "premium_reasoning", True),
    "differentiation": ("L1", "tier_premium", "premium_reasoning", True),
    "risk_legal": ("L1", "tier_premium", "premium_reasoning", True),
    "fact_lock_claim": ("L2", "script_only", "fact_lock_bundle", False),
    "implementation_claim": ("L2", "script_only", "verify_p0_paths", False),
    "legal_guarantee": ("L3", "human_only", "human", False),
    "qualification_warranty": ("L3", "human_only", "human", False),
}

VALID_GRANT_PROGRAMS = frozenset({"opendata_327", "open_innovation", "generic"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_tasks_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def route_task(task: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    task_id = str(task.get("task_id") or task.get("id") or "")
    if not task_id:
        raise ValueError("task missing task_id")

    kind = str(task.get("task_kind") or "").strip().lower()
    if kind not in LANE_MAP:
        raise ValueError(f"task {task_id}: unknown task_kind {kind!r}")

    lane_id, model_tier, model_slot_hint, invoke_llm = LANE_MAP[kind]
    grant_program = str(task.get("grant_program") or "generic").strip().lower()
    if grant_program not in VALID_GRANT_PROGRAMS:
        raise ValueError(f"task {task_id}: invalid grant_program {grant_program!r}")

    requires_human = model_tier == "human_only"
    requires_script_gate = model_tier == "script_only"

    return {
        "task_id": task_id,
        "task_kind": kind,
        "grant_program": grant_program,
        "lane_id": lane_id,
        "model_tier": model_tier,
        "model_slot_hint": model_slot_hint,
        "invoke_llm": invoke_llm and not dry_run,
        "invoke_llm_planned": invoke_llm,
        "dry_run": dry_run,
        "requires_human": requires_human,
        "requires_script_gate": requires_script_gate,
        "research_only": RESEARCH_ONLY,
        "notes": str(task.get("notes") or ""),
    }


def build_report(
    routes: list[dict[str, Any]],
    *,
    dry_run: bool,
    tasks_path: Path,
) -> dict[str, Any]:
    tier_counts: dict[str, int] = {}
    for r in routes:
        tier = str(r["model_tier"])
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    return {
        "schema": SCHEMA,
        "generated_at_utc": _now(),
        "research_only": RESEARCH_ONLY,
        "dry_run": dry_run,
        "tasks_jsonl": str(tasks_path.resolve()),
        "task_count": len(routes),
        "tier_counts": tier_counts,
        "forbidden": [
            "hwp_pms_auto_submit",
            "track_a_live_merge",
            "external_percent_headline",
            "unmeasured_api_unit_price_claim",
        ],
        "routes": routes,
        "ok": True,
    }


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks-jsonl", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--append-jsonl",
        type=Path,
        default=DEFAULT_JSONL,
        help="Append one summary line per run (metering / audit trail).",
    )
    ap.add_argument(
        "--no-append-jsonl",
        action="store_true",
        help="Skip append to grant_proposal_model_route_v1.jsonl",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="Mark invoke_llm true for LLM tiers (still no HTTP in v0).",
    )
    args = ap.parse_args()

    dry_run = not args.live
    tasks = load_tasks_jsonl(args.tasks_jsonl)
    if not tasks:
        raise SystemExit(f"no tasks in {args.tasks_jsonl}")

    routes = [route_task(t, dry_run=dry_run) for t in tasks]
    report = build_report(routes, dry_run=dry_run, tasks_path=args.tasks_jsonl)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_append_jsonl:
        append_jsonl(
            args.append_jsonl,
            {
                "schema": f"{SCHEMA}_run",
                "generated_at_utc": report["generated_at_utc"],
                "dry_run": dry_run,
                "task_count": report["task_count"],
                "tier_counts": report["tier_counts"],
                "out": str(args.out.resolve()),
            },
        )

    print(json.dumps({"ok": True, "out": str(args.out), "task_count": len(routes), "dry_run": dry_run}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
