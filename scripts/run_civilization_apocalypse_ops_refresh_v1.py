#!/usr/bin/env python3
"""Refresh civilization apocalypse B-track ops: registry, Brier, brief, parallel_ops ([HYPO])."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FIXTURE = ROOT / "tests/fixtures/general_prophecy_registry_civilization_apocalypse_v1.json"
REG_OUT = ROOT / "reports/general_prophecy_civilization_apocalypse_v1_latest.json"
BRIEF_OUT = ROOT / "reports/general_prophecy_civilization_apocalypse_brief_v1.md"
BRIER_OUT = ROOT / "reports/general_prophecy_civilization_apocalypse_brier_eval_v1.json"
PARALLEL_OUT = ROOT / "reports/civilization_apocalypse_parallel_ops_v1.json"


def _run(cmd: list[str]) -> int:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return cp.returncode


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=PARALLEL_OUT)
    args = ap.parse_args()

    steps: dict[str, int] = {}
    if FIXTURE.is_file():
        steps["generate_registry"] = _run(
            [
                PY,
                str(ROOT / "scripts/generate_general_prophecy_v1.py"),
                "-i",
                str(FIXTURE),
                "-o",
                str(REG_OUT),
            ]
        )
        steps["build_brief"] = _run(
            [
                PY,
                str(ROOT / "scripts/build_general_prophecy_brief.py"),
                "-i",
                str(REG_OUT),
                "-o",
                str(BRIEF_OUT),
            ]
        )
        steps["brier_eval"] = _run(
            [
                PY,
                str(ROOT / "scripts/eval_general_prophecy_brier_score.py"),
                "-i",
                str(REG_OUT),
                "-o",
                str(BRIER_OUT),
            ]
        )
    steps["sovereign_stack_brief"] = _run(
        [PY, str(ROOT / "scripts/build_track_c_risk_narrative_sovereign_stack_brief_v1.py")]
    )

    reg = _load(REG_OUT)
    brier = _load(BRIER_OUT)
    metrics = (brier or {}).get("metrics") or {}
    n_q = len((reg or {}).get("questions") or []) if reg else 0

    doc = {
        "schema": "civilization_apocalypse_parallel_ops_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "boundary_ack": True,
        "final_action": "WATCH_HYPOTHESIS_MATRIX",
        "lanes": {
            "brier_sandbox": {
                "status": "ok" if steps.get("brier_eval", 1) == 0 else "fail",
                "civilization_only": {
                    "registry": str(REG_OUT.relative_to(ROOT)).replace("\\", "/"),
                    "eval": str(BRIER_OUT.relative_to(ROOT)).replace("\\", "/"),
                    "n_questions": n_q,
                    "n_evaluated": metrics.get("n_evaluated"),
                    "pending_count": metrics.get("pending_count"),
                    "median_days_to_deadline": metrics.get("median_days_to_deadline"),
                    "mean_brier_score": metrics.get("mean_brier_score"),
                    "note": "Pending until resolve; not MS/Track A.",
                },
            },
            "sovereign_stack_brief": {
                "status": "ok" if steps.get("sovereign_stack_brief", 1) == 0 else "fail",
                "brief": "reports/track_c_risk_narrative_sovereign_stack_brief_v1.json",
                "watch": "reports/civilization_apocalypse_sovereign_stack_watch_v1.json",
            },
            "logos_chronology_hardset": {
                "status": "ok" if (_load(ROOT / "reports/logos_chronology_hardset_closure_v1_latest.json") or {}).get("ok") else "fail",
                "closure": "reports/logos_chronology_hardset_closure_v1_latest.json",
                "margin_report": "reports/logos_hardset_era_human_margin_report_v1_latest.md",
                "ms_citation": "historical text_blind 6.4% only",
                "hardset_ssot_hit_at_1": (
                    (_load(ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json") or {})
                    .get("summary", {})
                    .get("hit_at_1_strict")
                ),
            },
        },
        "track_wall": {"track_a_auto_promotion": False, "live_trading_trigger": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = all(code == 0 for code in steps.values())
    print(json.dumps({"ok": ok, "steps": steps, "n_questions": n_q, "pending": metrics.get("pending_count")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
