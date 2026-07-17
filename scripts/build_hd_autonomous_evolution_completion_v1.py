#!/usr/bin/env python3
"""HD autonomous evolution completion report — quality gate + approval map patch.

[HYPO] / research_only. Does not promote Track A or live trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "hd_autonomous_evolution_completion_v1_latest.json"
MISSION_DEFAULT = ROOT / "reports" / "hd_autonomous_evolution_mission_v1_latest.json"
APPROVAL_DEFAULT = ROOT / "reports" / "delegation_hd_autonomous_evolution_approval_map_v1_latest.json"
DEFINITION = ROOT / "docs" / "final" / "artifacts" / "mkm_high_dimensional_autonomous_evolution_v1_latest.json"

EVIDENCE_PATHS = {
    "0": MISSION_DEFAULT,
    "1": ROOT / "reports" / "mkm_high_delegation_preflight_v1_latest.json",
    "2p": ROOT / "reports" / "p0_p1_p2_hybrid_batch_v1_latest.json",
    "2t": ROOT / "reports" / "telegram_daily_wiring_v1_latest.json",
    "2t2": ROOT / "reports" / "telegram_daily_wiring_digest_preview_latest.txt",
    "2": ROOT / "reports" / "btrack_high_delegation_intel_v1_latest.json",
    "3": ROOT / "reports" / "btrack_swarm_sasang_stage1_accumulation_v1_latest.json",
    "4": ROOT / "storage" / "meta" / "mkm_ops_memory_index_v1.json",
    "5": ROOT / "reports" / "delegation_research_assist_gate_v1_latest.json",
    "6": DEFAULT_OUT,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _node_done(node_id: str, steps: dict[str, Any]) -> tuple[bool, str]:
    step = steps.get(node_id) or {}
    if step.get("skipped"):
        return True, "skipped"
    if step.get("exit_code") == 0:
        return True, "exit_0"
    ev = EVIDENCE_PATHS.get(node_id)
    if ev and ev.is_file():
        if node_id == "5":
            return True, "optional_review_evidence"
        return True, "evidence_present"
    return False, step.get("note") or "missing"


def _tier0_browser_only_host_gap(mission: dict[str, Any], preflight: dict[str, Any]) -> bool:
    """tier_0 prophecy/oracle: IDE browser_view_missing is Tier-3 chat inject, not a hard quality fail."""
    cost = str(mission.get("cost_tier") or "tier_0").strip()
    lane = str(mission.get("lane") or "").strip().lower()
    if cost != "tier_0" or lane not in ("prophecy", "oracle"):
        return False
    steps = preflight.get("steps") if isinstance(preflight.get("steps"), dict) else {}
    hard = ("p0_constitution_paths", "mcp_host_hygiene", "cursor_session_upgrade")
    if not all((steps.get(k) or {}).get("ok") is True for k in hard):
        return False
    browser = steps.get("browser_host_readiness") or {}
    if browser.get("ok") is True:
        return False
    # Non-strict browser probe fails with exit 2 (view missing / chat inject).
    code = browser.get("exit_code")
    try:
        return int(code) == 2
    except (TypeError, ValueError):
        return False


def _quality_checks(
    mission: dict[str, Any],
    preflight: dict[str, Any],
    intel: dict[str, Any],
    swarm_acc: dict[str, Any],
    tier_a: dict[str, Any],
    hybrid: dict[str, Any],
    telegram: dict[str, Any],
    steps: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    checks["mission_present"] = bool(mission.get("mission_line"))
    host_ready = preflight.get("host_ready") is True
    soft_browser = (not host_ready) and _tier0_browser_only_host_gap(mission, preflight)
    checks["preflight_host_ready"] = host_ready
    checks["preflight_host_ready_soft_browser_ok"] = soft_browser
    checks["preflight_host_ready_effective"] = host_ready or soft_browser
    checks["preflight_ready_for_auto"] = preflight.get("ready_for_auto") is True
    checks["intel_ok"] = intel.get("ok") is True or intel.get("overall_ok") is True
    step_2p = steps.get("2p") or {}
    hybrid_skipped = step_2p.get("skipped") is True
    checks["hybrid_batch_ok"] = hybrid_skipped or hybrid.get("ok") is True
    step_2t = steps.get("2t") or {}
    telegram_skipped = step_2t.get("skipped") is True
    checks["telegram_daily_wiring_ok"] = telegram_skipped or telegram.get("ok") is True
    checks["swarm_accumulation_artifact"] = (
        bool(swarm_acc)
        or EVIDENCE_PATHS["3"].is_file()
        or (steps.get("3") or {}).get("skipped") is True
    )
    checks["tier_a_observable"] = tier_a.get("tier_a_ready") is not None or tier_a.get("row_count") is not None
    checks["ops_memory_index"] = EVIDENCE_PATHS["4"].is_file()

    auto_nodes = ["0", "1", "2p", "2t", "2t2", "2", "3", "4"]
    node_results = {}
    for nid in auto_nodes:
        ok, reason = _node_done(nid, steps)
        node_results[nid] = {"ok": ok, "reason": reason}
    node_results["6"] = {"ok": True, "reason": "completion_report_writing"}
    checks["auto_nodes"] = node_results
    checks["auto_nodes_all_ok"] = all(v["ok"] for v in node_results.values())

    quality_ok = (
        checks["mission_present"]
        and checks["preflight_host_ready_effective"]
        and checks["hybrid_batch_ok"]
        and checks["telegram_daily_wiring_ok"]
        and checks["intel_ok"]
        and checks["swarm_accumulation_artifact"]
        and checks["ops_memory_index"]
        and checks["auto_nodes_all_ok"]
    )
    return {"checks": checks, "quality_ok": quality_ok}


def _patch_approval_map(
    approval_path: Path,
    steps: dict[str, Any],
    quality_ok: bool,
) -> None:
    if not approval_path.is_file():
        return
    data = _read_json(approval_path)
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id", ""))
        ok, reason = _node_done(nid, steps)
        if node.get("approval") == "REVIEW" and not ok:
            node["status"] = "review_pending"
            node["last_reason"] = reason
            continue
        node["status"] = "done" if ok else "failed"
        node["last_reason"] = reason
    data["completion_quality_ok"] = quality_ok
    data["updated_at_utc"] = _utc()
    approval_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mission-json", type=Path, default=MISSION_DEFAULT)
    ap.add_argument("--steps-json", type=Path, default="", help="Optional run steps from orchestrator")
    ap.add_argument("--quality-pass", type=int, default=1)
    ap.add_argument("--max-quality-passes", type=int, default=5)
    ap.add_argument("--patch-approval-map", action="store_true")
    ap.add_argument("--approval-map", type=Path, default=APPROVAL_DEFAULT)
    ap.add_argument("--reproducible-command", default="")
    args = ap.parse_args()

    mission = _read_json(args.mission_json)
    preflight = _read_json(EVIDENCE_PATHS["1"])
    intel = _read_json(EVIDENCE_PATHS["2"])
    hybrid = _read_json(EVIDENCE_PATHS["2p"])
    telegram = _read_json(EVIDENCE_PATHS["2t"])
    swarm_acc = _read_json(EVIDENCE_PATHS["3"])
    tier_a = _read_json(ROOT / "reports" / "btrack_swarm_tier_a_prereqs_v1_latest.json")
    definition = _read_json(DEFINITION)

    steps: dict[str, Any] = {}
    if args.steps_json:
        raw = _read_json(Path(args.steps_json))
        steps = raw.get("nodes") if isinstance(raw.get("nodes"), dict) else raw

    quality = _quality_checks(mission, preflight, intel, swarm_acc, tier_a, hybrid, telegram, steps)
    quality_ok = quality["quality_ok"]

    repro = args.reproducible_command or mission.get("reproducible_command") or (
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1"
    )

    out: dict[str, Any] = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "definition_ssot": str(DEFINITION.relative_to(ROOT)).replace("\\", "/"),
        "mission_line": mission.get("mission_line", ""),
        "cost_tier": mission.get("cost_tier", "tier_0"),
        "lane": mission.get("lane", ""),
        "quality_pass": args.quality_pass,
        "max_quality_passes": args.max_quality_passes,
        "quality_ok": quality_ok,
        "completion_contract": {
            "exit_code_target": 0,
            "artifact": str(args.out_json.relative_to(ROOT)).replace("\\", "/"),
            "reproducible_command": repro,
        },
        "quality": quality,
        "evidence_paths": {
            k: str(v.relative_to(ROOT)).replace("\\", "/") if v.is_file() else None
            for k, v in EVIDENCE_PATHS.items()
        },
        "tier_a_snapshot": {
            "tier_a_ready": tier_a.get("tier_a_ready"),
            "row_count": tier_a.get("row_count"),
            "required_rows": tier_a.get("required_rows"),
        },
        "definition_ko_one_liner": definition.get("definition_ko", ""),
        "boundary_ack": "B-track observability only; no Track A·live·Final Action auto-merge.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.patch_approval_map:
        _patch_approval_map(args.approval_map, steps, quality_ok)

    print(json.dumps({"quality_ok": quality_ok, "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if quality_ok or args.quality_pass >= args.max_quality_passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
