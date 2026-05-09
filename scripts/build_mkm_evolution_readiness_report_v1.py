#!/usr/bin/env python3
"""Build readiness report for 4h evolution loop and daily control tower autopush."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_evolution_readiness_report_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _schtasks(task_name: str) -> dict[str, Any]:
    cp = subprocess.run(
        ["schtasks", "/query", "/tn", task_name, "/v", "/fo", "LIST"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return {"task_name": task_name, "exists": False, "query_exit_code": cp.returncode}
    lines = [x.strip() for x in cp.stdout.splitlines() if ":" in x]
    kv: dict[str, str] = {}
    for line in lines:
        k, v = line.split(":", 1)
        kv[k.strip()] = v.strip()
    return {
        "task_name": task_name,
        "exists": True,
        "status": kv.get("Status"),
        "next_run_time": kv.get("Next Run Time"),
        "last_run_time": kv.get("Last Run Time"),
        "last_result": kv.get("Last Result"),
        "task_to_run": kv.get("Task To Run"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    evo_loop = _safe_json(ROOT / "docs" / "final" / "artifacts" / "evolution_lightweight_loop_latest.json")
    proposal = _safe_json(ROOT / "docs" / "final" / "artifacts" / "lens_evolution_proposal_latest.json")
    hit_rate = _safe_json(ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_per_lens_latest.json")

    task_4h = _schtasks("MKM_Evolution_Lightweight4h")
    task_autopush = _schtasks("MKM_BTrack_ControlTower_Autopush_Daily")

    proposals = proposal.get("proposals") if isinstance(proposal.get("proposals"), list) else []
    payload = {
        "schema": "mkm_evolution_readiness_report_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "human_signoff_required": True,
        "inputs": {
            "evolution_loop_latest": "docs/final/artifacts/evolution_lightweight_loop_latest.json",
            "lens_evolution_proposal_latest": "docs/final/artifacts/lens_evolution_proposal_latest.json",
            "prophecy_hit_rate_per_lens_latest": "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json",
        },
        "runtime_health": {
            "evolution_4h_task": task_4h,
            "autopush_daily_task": task_autopush,
        },
        "quality": {
            "loop_overall_ok": evo_loop.get("overall_ok"),
            "loop_triggered": evo_loop.get("triggered"),
            "proposal_count": len(proposals),
            "requires_human_approval": proposal.get("requires_human_approval"),
            "hit_rate_schema": hit_rate.get("schema"),
        },
        "readiness": {
            "autonomy_mode": "measured_autonomy_with_hitl",
            "safe_to_continue": bool(evo_loop.get("overall_ok") is True),
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
