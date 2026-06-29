#!/usr/bin/env python3
"""MKM Cursor continuity bench — 3 resume cycles, deep_fetch preservation ([HYPO])."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from append_mkm_cursor_turn_meta_v1 import build_turn_record, append_turn  # noqa: E402
from build_mkm_cursor_deep_handoff_envelope_v1 import (  # noqa: E402
    _read_json as read_envelope_json,
    build_envelope,
    validate_envelope,
)
from mkm_cursor_continuity_ssot_v1 import (  # noqa: E402
    REQUIRED_PATH_STRINGS,
    missing_required_paths,
    normalize_path,
    verify_required_files_exist,
)

DEFAULT_OUT = ROOT / "reports/mkm_cursor_continuity_bench_v1_latest.json"
DEFAULT_HANDOFF = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
DEFAULT_RESUME = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
DEFAULT_TIER3 = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_cmd(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def preservation_rate(baseline: list[str], final: list[str]) -> float:
    base = {normalize_path(p) for p in baseline if p}
    fin = {normalize_path(p) for p in final if p}
    if not base:
        return 0.0
    return round(len(base & fin) / len(base), 4)


def run_resume_cycles(
    *,
    lane: str,
    continuity_id: str,
    cycles: int,
    log_path: Path,
) -> dict[str, Any]:
    resume_pack = read_envelope_json(DEFAULT_RESUME)
    handoff = (
        read_envelope_json(DEFAULT_HANDOFF)
        if DEFAULT_HANDOFF.is_file()
        else {"schema": "ollama_shallow_router_handoff_v1", "deep_fetch_next": []}
    )
    tier3_index = read_envelope_json(DEFAULT_TIER3)

    cycle_rows: list[dict[str, Any]] = []
    baseline_queue: list[str] = []
    last_queue: list[str] = []
    orphan_total = 0

    if log_path.is_file():
        log_path.unlink()

    for i in range(1, cycles + 1):
        envelope = build_envelope(
            lane=lane,
            resume_pack=resume_pack,
            handoff=handoff,
            tier3_index=tier3_index,
            continuity_id=continuity_id,
        )
        errs = validate_envelope(envelope)
        if errs:
            raise RuntimeError(f"envelope cycle {i}: {'; '.join(errs)}")

        turn_doc = build_turn_record(
            lane=lane,
            continuity_id=continuity_id,
            envelope=envelope,
            checkpoint_message=f"bench-cycle-{i}",
        )
        append_turn(turn_doc, log_path)

        queue = list(turn_doc.get("deep_fetch_next") or [])
        if i == 1:
            baseline_queue = list(queue)
        last_queue = queue
        orphan_total += len(turn_doc.get("unverified_claims") or [])

        cycle_rows.append(
            {
                "cycle": i,
                "deep_fetch_count": len(queue),
                "required_ssot_missing": turn_doc.get("required_ssot_missing") or [],
                "orphan_claims": turn_doc.get("unverified_claims") or [],
            }
        )

    rate = preservation_rate(baseline_queue, last_queue)
    required_missing_final = missing_required_paths(last_queue)
    orphan_rate = round(orphan_total / max(cycles, 1), 4)
    fact_lock_skip_rate = round(
        len(verify_required_files_exist(ROOT)) / max(len(REQUIRED_PATH_STRINGS), 1),
        4,
    )

    return {
        "cycles": cycle_rows,
        "baseline_queue": baseline_queue,
        "final_queue": last_queue,
        "deep_fetch_preservation_rate": rate,
        "orphan_claim_rate": orphan_rate,
        "fact_lock_skip_rate": fact_lock_skip_rate,
        "required_ssot_missing_final": required_missing_final,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="infra")
    parser.add_argument("--continuity-id", default="p5-continuity-bench-fixture")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--min-preservation", type=float, default=0.8)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--log", type=Path, default=ROOT / "reports/mkm_cursor_continuity_bench_log.jsonl")
    parser.add_argument("--skip-repro", action="store_true")
    args = parser.parse_args()

    if args.cycles < 1:
        print("FAIL: --cycles must be >= 1", file=sys.stderr)
        return 1

    try:
        bench_core = run_resume_cycles(
            lane=args.lane,
            continuity_id=args.continuity_id,
            cycles=args.cycles,
            log_path=args.log,
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    repro_steps: list[dict[str, Any]] = []
    if not args.skip_repro:
        repro_steps = [
            _run_cmd([sys.executable, "scripts/bench_mkm_ltm_resume_lane_token_v1.py"]),
            _run_cmd([sys.executable, "scripts/bench_mkm_ltm_route_accuracy_v1.py"]),
            _run_cmd([sys.executable, "scripts/check_mkm_ltm_lane_purity_v1.py"]),
        ]

    doc: dict[str, Any] = {
        "schema": "mkm_cursor_continuity_bench_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "lane": args.lane,
        "continuity_id": args.continuity_id,
        "cycle_count": args.cycles,
        "aggregate": {
            "deep_fetch_preservation_rate": bench_core["deep_fetch_preservation_rate"],
            "orphan_claim_rate": bench_core["orphan_claim_rate"],
            "fact_lock_skip_rate": bench_core["fact_lock_skip_rate"],
            "required_ssot_missing_final": bench_core["required_ssot_missing_final"],
            "gate_min_preservation": args.min_preservation,
            "preservation_pass": bench_core["deep_fetch_preservation_rate"] >= args.min_preservation,
            "required_ssot_pass": not bench_core["required_ssot_missing_final"],
        },
        "cycles": bench_core["cycles"],
        "baseline_queue": bench_core["baseline_queue"],
        "final_queue": bench_core["final_queue"],
        "bench_repro_subset": repro_steps,
        "reproducible_command": (
            f"py scripts/run_mkm_cursor_continuity_bench_v1.py --lane {args.lane} "
            f"--continuity-id {args.continuity_id}"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"deep_fetch_preservation_rate={bench_core['deep_fetch_preservation_rate']} "
        f"orphan_claim_rate={bench_core['orphan_claim_rate']} "
        f"required_ssot_missing_final={bench_core['required_ssot_missing_final']}"
    )

    ok = (
        bench_core["deep_fetch_preservation_rate"] >= args.min_preservation
        and not bench_core["required_ssot_missing_final"]
    )
    if not args.skip_repro:
        ok = ok and all(step["ok"] for step in repro_steps)

    if not ok:
        print("FAIL: continuity bench gate not met", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
