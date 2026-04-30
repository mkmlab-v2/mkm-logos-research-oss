#!/usr/bin/env python3
"""Run end-to-end HOLD rehearsal for genius human review gate and recover."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_GOLDSET = ART / "genius_reasoning_human_goldset_v1.json"
DEFAULT_OUT = ART / "genius_human_review_hold_rehearsal_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(script_name: str, args: list[str]) -> tuple[int, str]:
    cmd = ["py", str(ROOT / "scripts" / script_name), *args]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (cp.stdout or "").strip()
    err = (cp.stderr or "").strip()
    merged = out if out else err
    return cp.returncode, merged


def _run_hold_cycle(*, strict_gate: bool) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    plan: list[tuple[str, list[str], Path]] = [
        (
            "build_queue",
            [
                "--goldset-json",
                str(ART / "genius_reasoning_human_goldset_v1.json"),
                "--output-queue-json",
                str(ART / "genius_reasoning_human_review_queue_latest.json"),
                "--output-queue-csv",
                str(ART / "genius_reasoning_human_review_queue_latest.csv"),
            ],
            ART / "genius_reasoning_human_review_queue_latest.json",
        ),
        (
            "check_gate",
            [
                "--queue-json",
                str(ART / "genius_reasoning_human_review_queue_latest.json"),
                "--output-json",
                str(ART / "genius_reasoning_human_review_gate_latest.json"),
                "--max-pending-count",
                "0" if strict_gate else "2",
                "--max-pending-ratio",
                "0.0" if strict_gate else "0.15",
            ],
            ART / "genius_reasoning_human_review_gate_latest.json",
        ),
        (
            "dispatch_gate",
            [
                "--gate-json",
                str(ART / "genius_reasoning_human_review_gate_latest.json"),
                "--output-json",
                str(ART / "genius_reasoning_human_review_gate_dispatch_latest.json"),
            ],
            ART / "genius_reasoning_human_review_gate_dispatch_latest.json",
        ),
        (
            "append_gate_history",
            [
                "--gate-json",
                str(ART / "genius_reasoning_human_review_gate_latest.json"),
                "--history-jsonl",
                str(ART / "genius_reasoning_human_review_gate_history_log.jsonl"),
            ],
            ART / "genius_reasoning_human_review_gate_history_log.jsonl",
        ),
        (
            "check_gate_trend",
            [
                "--history-jsonl",
                str(ART / "genius_reasoning_human_review_gate_history_log.jsonl"),
                "--output-json",
                str(ART / "genius_reasoning_human_review_gate_trend_latest.json"),
                "--window",
                "1",
                "--max-hold-count",
                "0",
                "--max-pending-ratio-avg",
                "0.0",
            ],
            ART / "genius_reasoning_human_review_gate_trend_latest.json",
        ),
        (
            "dispatch_gate_trend",
            [
                "--trend-json",
                str(ART / "genius_reasoning_human_review_gate_trend_latest.json"),
                "--output-json",
                str(ART / "genius_reasoning_human_review_gate_trend_dispatch_latest.json"),
            ],
            ART / "genius_reasoning_human_review_gate_trend_dispatch_latest.json",
        ),
        (
            "append_dispatch_health_history",
            [
                "--alert-dispatch-json",
                str(ART / "genius_reasoning_benchmark_alert_dispatch_latest.json"),
                "--human-review-dispatch-json",
                str(ART / "genius_reasoning_human_review_gate_dispatch_latest.json"),
                "--human-review-trend-dispatch-json",
                str(ART / "genius_reasoning_human_review_gate_trend_dispatch_latest.json"),
                "--history-jsonl",
                str(ART / "genius_reasoning_dispatch_health_history_log.jsonl"),
            ],
            ART / "genius_reasoning_dispatch_health_history_log.jsonl",
        ),
        (
            "check_dispatch_health_gate",
            [
                "--history-jsonl",
                str(ART / "genius_reasoning_dispatch_health_history_log.jsonl"),
                "--output-json",
                str(ART / "genius_reasoning_dispatch_health_gate_latest.json"),
                "--window",
                "1",
                "--max-failed-count",
                "1",
                "--max-unconfigured-count",
                "1",
            ],
            ART / "genius_reasoning_dispatch_health_gate_latest.json",
        ),
    ]

    script_map = {
        "build_queue": "build_genius_reasoning_human_review_queue_v1.py",
        "check_gate": "check_genius_reasoning_human_review_gate_v1.py",
        "dispatch_gate": "dispatch_genius_reasoning_human_review_gate_webhook_v1.py",
        "append_gate_history": "append_genius_reasoning_human_review_gate_history_v1.py",
        "check_gate_trend": "check_genius_reasoning_human_review_gate_trend_v1.py",
        "dispatch_gate_trend": "dispatch_genius_reasoning_human_review_trend_webhook_v1.py",
        "append_dispatch_health_history": "append_genius_reasoning_dispatch_health_history_v1.py",
        "check_dispatch_health_gate": "check_genius_reasoning_dispatch_health_gate_v1.py",
    }

    for name, args, output_path in plan:
        rc, msg = _run_py(script_map[name], args)
        step = {
            "name": name,
            "exit_code": rc,
            "output": msg,
            "output_path": str(output_path).replace("\\", "/"),
        }
        steps.append(step)
        if rc != 0:
            break
    return {"steps": steps}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goldset-json", type=Path, default=DEFAULT_GOLDSET)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rehearsal-reviewer", type=str, default="chaos_drill")
    args = ap.parse_args()

    original = _read_json(args.goldset_json)
    rows = original.get("rows") if isinstance(original.get("rows"), list) else []
    if not rows:
        out = {
            "schema": "genius_human_review_hold_rehearsal_v1",
            "generated_at_utc": _iso_now(),
            "pass": False,
            "error": "goldset_rows_empty",
        }
        _write_json(args.output_json, out)
        print(json.dumps({"ok": False, "error": "goldset_rows_empty"}, ensure_ascii=False))
        return 1

    target_idx = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if str(row.get("review_status") or "").lower() == "approved":
            target_idx = i
            break
    if target_idx is None:
        target_idx = 0

    # 1) Force one row to draft to trigger HOLD.
    mutated = json.loads(json.dumps(original))
    mrows = mutated.get("rows") if isinstance(mutated.get("rows"), list) else []
    target = mrows[target_idx]
    if isinstance(target, dict):
        target["review_status"] = "draft"
        target["reviewer"] = args.rehearsal_reviewer
        target["reviewed_at_utc"] = ""
        target["note"] = "hold rehearsal forced draft row"
    _write_json(args.goldset_json, mutated)

    hold_cycle = _run_hold_cycle(strict_gate=True)
    hold_gate = _read_json(ART / "genius_reasoning_human_review_gate_latest.json")
    hold_trend = _read_json(ART / "genius_reasoning_human_review_gate_trend_latest.json")

    # 2) Restore original goldset and recover normal state.
    _write_json(args.goldset_json, original)
    recover_cycle = _run_hold_cycle(strict_gate=False)
    recover_gate = _read_json(ART / "genius_reasoning_human_review_gate_latest.json")
    recover_trend = _read_json(ART / "genius_reasoning_human_review_gate_trend_latest.json")

    hold_ok = str(hold_gate.get("status") or "") == "HOLD"
    hold_trend_ok = str(hold_trend.get("status") or "") == "HOLD"
    recover_ok = str(recover_gate.get("status") or "") == "PASS"
    recover_trend_ok = str(recover_trend.get("status") or "") == "PASS"
    drill_pass = hold_ok and hold_trend_ok and recover_ok and recover_trend_ok

    out = {
        "schema": "genius_human_review_hold_rehearsal_v1",
        "generated_at_utc": _iso_now(),
        "goldset_json": str(args.goldset_json).replace("\\", "/"),
        "forced_row_index": target_idx,
        "hold_phase": {
            "gate_status": hold_gate.get("status"),
            "trend_status": hold_trend.get("status"),
            "steps": hold_cycle.get("steps"),
        },
        "recovery_phase": {
            "gate_status": recover_gate.get("status"),
            "trend_status": recover_trend.get("status"),
            "steps": recover_cycle.get("steps"),
        },
        "pass": drill_pass,
    }
    _write_json(args.output_json, out)
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "pass": drill_pass}, ensure_ascii=False))
    return 0 if drill_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
