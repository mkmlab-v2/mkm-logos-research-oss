#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run full June gate bundle when forward n_scored≥15; else emit wait status [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _default_as_of_kst  # noqa: E402

READINESS = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_gate_reached_bundle_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_py(script: str, *args: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "script": script,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "").strip()[-500:],
        "stderr_tail": (proc.stderr or "").strip()[-500:],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--min-scored", type=int, default=15)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--force", action="store_true", help="Run bundle even if n_scored < min (research only)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    readiness = _read_json(args.readiness_json)
    fs = readiness.get("forward_scoring") if isinstance(readiness.get("forward_scoring"), dict) else {}
    n_scored = int(fs.get("n_scored") or 0)
    min_required = int(fs.get("min_required") or args.min_scored)
    as_of = args.as_of_kst or _default_as_of_kst()
    gate_reached = n_scored >= min_required

    steps: list[dict[str, Any]] = []
    doc: dict[str, Any] = {
        "schema": "kospi_june2026_gate_reached_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "forward_gate": {
            "n_scored": n_scored,
            "min_required": min_required,
            "gate_reached": gate_reached,
            "projected_gate_session_date": fs.get("projected_gate_session_date"),
            "as_of_kst": as_of,
        },
        "steps": steps,
    }

    if not gate_reached and not args.force:
        doc["status"] = "wait"
        doc["verdict_ko"] = (
            f"gate 미달 n={n_scored}/{min_required} — full 4AI cross·promotion 재판정 skip. "
            f"ETA {fs.get('projected_gate_session_date') or 'TBD'}"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WAIT: n_scored={n_scored}/{min_required} — WROTE {args.output.resolve()}")
        return 0

    cal = str(args.calendar_json)
    for script, sargs in (
        ("scripts/build_kospi_june2026_4ai_lock_unlock_hr_cross_v1.py", ("--calendar-json", cal, "--as-of-kst", as_of)),
        ("scripts/build_kospi_june2026_promotion_readiness_v1.py", ("--year-month", "2026-06")),
        ("scripts/run_kospi_june2026_prophecy_evolution_v1.py", ()),
        ("scripts/build_kospi_june2026_wf_prefilter_drift_digest_v1.py", ()),
    ):
        step = _run_py(script, *sargs)
        steps.append(step)

    doc["status"] = "ran_full_bundle" if gate_reached else "forced_partial"
    doc["verdict_ko"] = (
        "June forward gate 충족 — full cross+readiness+evolution dry-run 완료. apply는 human sign-off만."
        if gate_reached
        else f"force run at n={n_scored} — 결과 partial, apply 금지"
    )
    doc["all_steps_ok"] = all(s.get("exit_code") == 0 for s in steps)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} status={doc['status']} "
        f"all_ok={doc['all_steps_ok']}"
    )
    return 0 if doc["all_steps_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
