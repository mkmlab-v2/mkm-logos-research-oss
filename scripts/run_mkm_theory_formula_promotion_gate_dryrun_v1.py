#!/usr/bin/env python3
"""P5 dry-run: wire theory promotion registry to B-track sasang/compression gate artifacts."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_gate_dryrun_v1_latest.json"

SASANG_CHAIN = ROOT / "scripts/run_sasang12_promotion_candidate_chain_v1.py"
SASANG_GATE = ROOT / "docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json"
COMPRESSION_GATE = ROOT / "scripts/check_compression_narrative_fact_lock_v1.py"
COMPRESSION_ART = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"artifact": str(path), "ok": False, "error": "missing"}
    doc = _load(path)
    return {
        "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
        "ok": True,
        "status": doc.get("status"),
        "promotion_to_a_track_allowed": doc.get("track_wall", {}).get(
            "promotion_to_a_track_allowed", doc.get("promotion_to_a_track_allowed")
        ),
    }


def main() -> int:
    if not REGISTRY.is_file():
        raise SystemExit(f"missing {REGISTRY}")

    registry = _load(REGISTRY)
    entries = registry.get("entries", [])
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for row in entries:
        lane = str(row.get("promotion_lane", "unknown"))
        by_lane.setdefault(lane, []).append(row)

    checks: list[dict[str, Any]] = []

    # Sasang B-track chain refresh (observation-only; no Track A bind)
    chain_exit = 2
    if SASANG_CHAIN.is_file():
        r = subprocess.run([sys.executable, str(SASANG_CHAIN)], cwd=ROOT, capture_output=True, text=True)
        chain_exit = r.returncode
    checks.append(
        {
            "name": "sasang12_chain",
            "lane": "sasang12_judge_btrack",
            "slot_count": len(by_lane.get("sasang12_judge_btrack", [])),
            "script": str(SASANG_CHAIN.relative_to(ROOT)).replace("\\", "/"),
            "exit_code": chain_exit,
            "ok": chain_exit == 0,
        }
    )
    sasang_gate = _gate_snapshot(SASANG_GATE)
    sasang_gate["name"] = "sasang12_gate_artifact"
    sasang_gate["lane"] = "sasang12_judge_btrack"
    sasang_gate["ok"] = sasang_gate.get("ok") and sasang_gate.get("status") in ("PASS", "FAIL")
    checks.append(sasang_gate)

    comp_script_ok = COMPRESSION_GATE.is_file()
    comp_exit = 2
    comp_report_path = ROOT / "reports/compression_narrative_fact_lock_theory_dryrun_latest.json"
    comp_violations = 0
    if comp_script_ok:
        r = subprocess.run(
            [
                sys.executable,
                str(COMPRESSION_GATE),
                "--out-json",
                str(comp_report_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        comp_exit = r.returncode
        if comp_report_path.is_file():
            comp_doc = _load(comp_report_path)
            comp_violations = int(comp_doc.get("violation_count", 0))
    checks.append(
        {
            "name": "compression_narrative_fact_lock",
            "lane": "compression_operational",
            "script": str(COMPRESSION_GATE.relative_to(ROOT)).replace("\\", "/"),
            "artifact": str(comp_report_path.relative_to(ROOT)).replace("\\", "/"),
            "exit_code": comp_exit,
            "violation_count": comp_violations,
            "ok": comp_exit == 0,
        }
    )

    comp_art = _gate_snapshot(COMPRESSION_ART)
    comp_art["name"] = "compression_active_report"
    comp_art["lane"] = "compression_operational"
    comp_art["slot_count"] = len(by_lane.get("compression_operational", []))
    checks.append(comp_art)

    checks.append(
        {
            "name": "compression_gate_script_present",
            "lane": "compression_operational",
            "script": str(COMPRESSION_GATE.relative_to(ROOT)).replace("\\", "/"),
            "ok": comp_script_ok,
        }
    )

    checks.append(
        {
            "name": "registry_track_wall",
            "promotion_to_a_track_allowed": registry.get("promotion_to_a_track_allowed"),
            "entries": len(entries),
            "lane_counts": registry.get("lane_counts", {}),
            "ok": registry.get("promotion_to_a_track_allowed") is False and len(entries) == 75,
        }
    )

    doc = {
        "schema": "mkm_theory_formula_promotion_gate_dryrun_v1",
        "generated_at_utc": utc_now(),
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "checks": checks,
        "ok": all(c.get("ok") for c in checks),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "ok": doc["ok"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
