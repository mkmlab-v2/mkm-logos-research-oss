#!/usr/bin/env python3
"""Append one weekly internal baseline row for Agent Handoff Governance pilot."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = SCRIPT_ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
LIFECYCLE_AUDIT = SCRIPT_ROOT / "reports/workspace_lifecycle_audit_v1_latest.json"
RESUME_PACK = SCRIPT_ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
LOG_PATH = SCRIPT_ROOT / "reports/agent_handoff_governance_weekly_baseline_v1.jsonl"
SUMMARY_PATH = SCRIPT_ROOT / "reports/agent_handoff_governance_weekly_baseline_summary_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_log_rows() -> list[dict[str, Any]]:
    if not LOG_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_row(
    *,
    lane: str,
    ops_memory_exit_code: int | None,
    cadence_note: str | None = None,
) -> dict[str, Any]:
    bench = _read_json(BENCH_PATH) or {}
    lifecycle = _read_json(LIFECYCLE_AUDIT) or {}
    resume = _read_json(RESUME_PACK) or {}
    off = bench.get("resume_pack_inject_off", {})
    on = bench.get("resume_pack_inject_on", {})
    full = bench.get("full_anchor_slices", {})
    delta = bench.get("delta_vs_full_slices", {})

    ops_step = None
    for step in lifecycle.get("steps") or []:
        if step.get("name") == "ops_memory_infra_lane":
            ops_step = step
            break

    row: dict[str, Any] = {
        "schema": "agent_handoff_governance_weekly_baseline_v1",
        "recorded_at_utc": _utc_now(),
        "track": "B",
        "research_only": True,
        "pilot_status": "internal_baseline",
        "customer_id": None,
        "lane": lane,
        "inject_off_tokens": off.get("tokens"),
        "inject_on_tokens_slice_1200": on.get("tokens"),
        "full_anchor_tokens_top3": full.get("tokens"),
        "reduction_percent_vs_full": delta.get("reduction_percent"),
        "token_method": off.get("method", "tiktoken:cl100k_base"),
        "must_keep_gate_implied": ops_memory_exit_code == 0 if ops_memory_exit_code is not None else None,
        "ops_memory_exit_code": ops_memory_exit_code,
        "lifecycle_audit_status": lifecycle.get("status"),
        "lifecycle_audit_utc": lifecycle.get("generated_at_utc"),
        "ops_memory_step_exit": (ops_step or {}).get("exit_code"),
        "c_free_gb": lifecycle.get("c_free_gb"),
        "resume_pack_generated_at_utc": resume.get("generated_at_utc"),
        "evidence": {
            "bench": str(BENCH_PATH.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
            "lifecycle": str(LIFECYCLE_AUDIT.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
            "resume_pack": str(RESUME_PACK.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        },
    }
    if cadence_note:
        row["cadence_note"] = cadence_note
    return row


def write_summary(rows: list[dict[str, Any]]) -> None:
    last = rows[-1] if rows else {}
    ok_streak = 0
    for row in reversed(rows):
        if row.get("ops_memory_exit_code") == 0 and row.get("lifecycle_audit_status") == "ok":
            ok_streak += 1
        else:
            break
    summary = {
        "schema": "agent_handoff_governance_weekly_baseline_summary_v1",
        "generated_at_utc": _utc_now(),
        "row_count": len(rows),
        "target_weeks_internal_baseline": 4,
        "ok_streak_lifecycle_and_ops_memory": ok_streak,
        "ready_for_customer_pilot": ok_streak >= 4,
        "last_row": last,
        "log_path": str(LOG_PATH.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        "boundary_ack": "internal baseline only — not customer SLA",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", default="infra", choices=["infra", "oracle", "ms"])
    ap.add_argument("--ops-memory-exit-code", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--cadence-note",
        default=None,
        help="Optional honesty tag e.g. daily_burst when multiple runs same calendar day.",
    )
    args = ap.parse_args()

    if not BENCH_PATH.is_file():
        print(f"FAIL: missing bench {BENCH_PATH}", flush=True)
        return 1

    row = build_row(
        lane=args.lane,
        ops_memory_exit_code=args.ops_memory_exit_code,
        cadence_note=args.cadence_note,
    )
    if args.dry_run:
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows = _load_log_rows()
    write_summary(rows)
    print(f"APPENDED: {LOG_PATH} (rows={len(rows)})")
    print(f"WROTE: {SUMMARY_PATH}")
    print(f"ok_streak: {rows and json.loads(SUMMARY_PATH.read_text())['ok_streak_lifecycle_and_ops_memory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
