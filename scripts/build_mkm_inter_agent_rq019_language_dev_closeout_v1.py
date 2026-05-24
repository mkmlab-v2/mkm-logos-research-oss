#!/usr/bin/env python3
"""M28: Operator closeout pack for RQ-019 language-dev lane (M12–M27, research_only)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_language_dev_closeout_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def build_closeout() -> dict[str, Any]:
    status = _load("docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json")
    ops = _load("docs/final/artifacts/mkm_inter_agent_rq019_ops_slice_v1_latest.json")
    weekly = _load("docs/final/artifacts/mkm_inter_agent_rq019_weekly_smoke_readiness_v1_latest.json")
    index = _load("docs/final/artifacts/mkm_inter_agent_rq019_milestone_artifact_index_v1_latest.json")
    regression = _load("docs/final/artifacts/mkm_inter_agent_rq019_regression_chain_v1_latest.json")

    if not status:
        return {"ok": False, "error": "encoding_status_missing"}

    lang_ready = bool(status.get("rq_019_language_dev_m12_m27_ready"))
    deps_ok = bool((ops or {}).get("ok")) and bool((weekly or {}).get("ok")) and bool((regression or {}).get("ok"))
    index_count = int((index or {}).get("milestone_count") or 0)

    doc = {
        "ok": lang_ready and deps_ok and index_count >= 27,
        "schema": "mkm_inter_agent_rq019_language_dev_closeout_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "rq_019": status.get("rq_019"),
        "language_dev_lane": {
            "m12_m27_ready": lang_ready,
            "milestone_count": (index or {}).get("milestone_count"),
            "weekly_smoke_ready": (weekly or {}).get("ok"),
            "regression_quick_ok": (regression or {}).get("ok"),
        },
        "operator_runbook": {
            "weekly_smoke": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1",
            "register_weekly_task": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/Register-MkmInterAgentRq019WeeklySmokeTask.ps1"
            ),
            "parallel_bundle": "py scripts/run_mkm_inter_agent_parallel_bundle_v1.py --max-workers 14",
            "trackc_dashboard": "py scripts/build_mkm_trackc_ops_dashboard_v1.py",
            "encoding_status": "py scripts/build_mkm_inter_agent_encoding_status_v1.py --skip-pytest",
        },
        "pointers": {
            "encoding_status": "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
            "ops_slice": "docs/final/artifacts/mkm_inter_agent_rq019_ops_slice_v1_latest.json",
            "milestone_index": "docs/final/artifacts/mkm_inter_agent_rq019_milestone_artifact_index_v1_latest.json",
            "weekly_smoke_readiness": "docs/final/artifacts/mkm_inter_agent_rq019_weekly_smoke_readiness_v1_latest.json",
            "trackc_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "commander_close": "docs/final/artifacts/mkm_inter_agent_rq019_commander_close_v1_latest.json",
        },
        "disclaimer_ko": (ops or {}).get("m3_public_copy_ko_one_line"),
        "boundary_ack": (
            "Language-dev closeout is B-track operator handoff only; "
            "not Track A promotion, live trading, or lingua franca completion."
        ),
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_closeout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
