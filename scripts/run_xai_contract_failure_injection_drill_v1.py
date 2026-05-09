#!/usr/bin/env python3
"""Inject deliberate contract failures for drill verification and evaluate."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESPONSES = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_responses_latest.json"
BACKUP = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_responses_backup_before_injection_latest.json"
SUMMARY = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failure_injection_drill_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _inject(doc: dict[str, Any], qids: list[str]) -> tuple[int, list[str]]:
    rows = doc.get("responses")
    if not isinstance(rows, list):
        return 0, []
    touched = 0
    applied: list[str] = []
    wanted = set(qids)
    for row in rows:
        if not isinstance(row, dict):
            continue
        q = row.get("question") if isinstance(row.get("question"), dict) else {}
        qid = str(q.get("question_id") or "")
        if qid not in wanted:
            continue
        # break contract deliberately
        row["evidence"] = []
        row["limitation"] = {"limitation_one": ""}
        row["action_guide"] = {"action_guide_one": ""}
        ev = row.get("evaluation")
        if not isinstance(ev, dict):
            ev = {}
            row["evaluation"] = ev
        ev["evidence_count_ok"] = False
        ev["has_limitation"] = False
        ev["has_action_guide"] = False
        ev["contract_pass"] = False
        ev["review_note"] = "failure_injection_drill_v1"
        touched += 1
        applied.append(qid)
    return touched, applied


def _run_eval(min_pass_rate: float) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "run_xai_contract_eval_v1.py"), "--min-pass-rate", str(min_pass_rate)]
    return subprocess.call(cmd, cwd=str(ROOT))


def _run_top5() -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_xai_contract_failures_top5_report_v1.py")]
    return subprocess.call(cmd, cwd=str(ROOT))


def _run_queue() -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_xai_action_queue_ops_v1.py"), "--default-owner", "xai-ops", "--due-days", "2"]
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--question-ids", default="q02,q07,q15")
    ap.add_argument("--min-pass-rate", type=float, default=0.95)
    ap.add_argument("--restore-after", action="store_true")
    ns = ap.parse_args()

    qids = [q.strip() for q in ns.question_ids.split(",") if q.strip()]
    if not RESPONSES.is_file():
        print(f"missing responses: {RESPONSES}", file=sys.stderr)
        return 2

    original = _load(RESPONSES)
    _write(BACKUP, original)
    work = json.loads(json.dumps(original))
    touched, applied = _inject(work, qids)
    _write(RESPONSES, work)

    eval_exit = _run_eval(ns.min_pass_rate)
    top5_exit = _run_top5()
    queue_exit = _run_queue()

    summary = {
        "schema": "xai_contract_failure_injection_drill_v1",
        "generated_at_utc": _utc_now(),
        "question_ids_requested": qids,
        "question_ids_applied": applied,
        "touched_count": touched,
        "eval_exit_code": eval_exit,
        "top5_exit_code": top5_exit,
        "queue_exit_code": queue_exit,
        "backup_path": str(BACKUP).replace("\\", "/"),
        "responses_path": str(RESPONSES).replace("\\", "/"),
        "restore_after": bool(ns.restore_after),
    }

    if ns.restore_after:
        _write(RESPONSES, original)
        # restore normal artifacts after drill
        _run_eval(0.95)
        _run_top5()
        _run_queue()
        summary["restored"] = True
    else:
        summary["restored"] = False

    _write(SUMMARY, summary)
    print(str(SUMMARY.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
