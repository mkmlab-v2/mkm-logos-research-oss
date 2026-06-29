#!/usr/bin/env python3
"""HD oracle L1-A Design fuse — 4D RAG inference graph overlay + showroom viz (tier_0).

  py scripts/run_mkm_hd_oracle_design_fuse_l1a_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MISSION_OUT = ROOT / "reports/hd_autonomous_evolution_mission_v1_latest.json"
COMPLETION_OUT = ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json"
STEPS_OUT = ROOT / "reports/hd_autonomous_evolution_run_steps_v1_latest.json"
PREFLIGHT = ROOT / "reports/mkm_high_delegation_preflight_v1_latest.json"
OVERLAY = ROOT / "docs/final/artifacts/logos_oracle_inference_graph_overlay_v1_latest.json"
SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFINITION = ROOT / "docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json"

DEFAULT_MISSION = (
    "Oracle L1-A Design fuse A1-A3 — 4D family legend + inference pipeline overlay "
    "+ sidecar freshness wire · tier_0 · B-track HOLD · cap bloom 금지"
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> int:
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    return int(proc.returncode or 0)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mission", default=DEFAULT_MISSION)
    ap.add_argument("--lane", default="oracle")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-mkmlife-build", action="store_true")
    args = ap.parse_args()

    repro = (
        "py scripts/run_mkm_hd_oracle_design_fuse_l1a_chain_v1.py "
        f'--mission "{args.mission}"'
    )
    mission = {
        "schema": "hd_autonomous_evolution_mission_v1",
        "generated_at_utc": _utc(),
        "mission_line": args.mission,
        "lane": args.lane,
        "cost_tier": "tier_0",
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "boundary_ack": "L1-A viz overlay; no cap bump, no Track A, no SEND OPEN.",
        "reproducible_command": repro,
        "definition_ssot": str(DEFINITION.relative_to(ROOT)).replace("\\", "/"),
    }
    MISSION_OUT.write_text(json.dumps(mission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    steps: dict[str, Any] = {}
    quality_ok = True

    pf = _read_json(PREFLIGHT)
    browser_optional_fail = (pf.get("steps") or {}).get("browser_host_readiness", {}).get("ok") is False
    p0_ok = (pf.get("steps") or {}).get("p0_constitution_paths", {}).get("ok") is True
    upgrade_ok = (pf.get("steps") or {}).get("cursor_session_upgrade", {}).get("ok") is True
    steps["preflight_snapshot"] = {
        "exit_code": 0 if p0_ok and upgrade_ok else 1,
        "ok": p0_ok and upgrade_ok,
        "note": "browser_host_optional_fail=" + str(browser_optional_fail),
        "skipped": False,
        "at_utc": _utc(),
    }

    l1a_cmd = [sys.executable, "scripts/run_logos_oracle_design_fuse_l1a_chain_v1.py"]
    if args.skip_pytest:
        l1a_cmd.append("--skip-pytest")
    if args.skip_mkmlife_build:
        l1a_cmd.append("--skip-mkmlife-build")
    code = _run(l1a_cmd)
    overlay_doc = _read_json(OVERLAY)
    slice_doc = _read_json(SLICE)
    l1a = overlay_doc.get("l1a_phases") or {}
    steps["l1a_design_fuse"] = {
        "exit_code": code,
        "ok": code == 0
        and l1a.get("A1_four_d_families") is True
        and l1a.get("A2_pipeline_path_overlay") is True
        and l1a.get("A3_sidecar_freshness_wire") is True
        and bool(slice_doc.get("inference_overlay")),
        "note": f"overlay_families={len(overlay_doc.get('four_d_families') or [])} "
        f"slice_nodes={((slice_doc.get('stats') or {}).get('node_count'))}",
        "skipped": False,
        "at_utc": _utc(),
    }
    if not steps["l1a_design_fuse"]["ok"]:
        quality_ok = False

    if not args.skip_pytest:
        code = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_build_logos_oracle_inference_graph_overlay_v1.py",
                "-q",
            ]
        )
        steps["pytest_overlay"] = {
            "exit_code": code,
            "ok": code == 0,
            "note": "test_build_logos_oracle_inference_graph_overlay_v1.py",
            "skipped": False,
            "at_utc": _utc(),
        }
        if code != 0:
            quality_ok = False

    STEPS_OUT.write_text(
        json.dumps(
            {
                "schema": "hd_autonomous_evolution_run_steps_v1",
                "quality_pass": 1,
                "max_passes": 1,
                "started_at_utc": _utc(),
                "nodes": steps,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "definition_ssot": str(DEFINITION.relative_to(ROOT)).replace("\\", "/"),
        "mission_line": args.mission,
        "cost_tier": "tier_0",
        "lane": args.lane,
        "quality_pass": 1,
        "max_quality_passes": 1,
        "quality_ok": quality_ok,
        "completion_contract": {
            "exit_code_target": 0,
            "artifact": str(COMPLETION_OUT.relative_to(ROOT)).replace("\\", "/"),
            "reproducible_command": repro,
        },
        "l1a_quality": {
            "A1_four_d_families": l1a.get("A1_four_d_families"),
            "A2_pipeline_path_overlay": l1a.get("A2_pipeline_path_overlay"),
            "A3_sidecar_freshness_wire": l1a.get("A3_sidecar_freshness_wire"),
            "sidecar_wire_status": (overlay_doc.get("sidecar_freshness") or {}).get("wire_status"),
            "router_hit_rate_structural": (overlay_doc.get("router_snapshot") or {}).get(
                "router_hit_rate"
            ),
            "observation_pass": (overlay_doc.get("passive_observability") or {}).get(
                "observation_pass"
            ),
            "browser_host_optional_fail": browser_optional_fail,
            "excluded_by_design": [
                "bloom_cap_bump",
                "narrative_201_plus",
                "track_a_promotion",
                "send_gate_open",
            ],
        },
        "evidence_paths": {
            "overlay": str(OVERLAY.relative_to(ROOT)).replace("\\", "/"),
            "slice": str(SLICE.relative_to(ROOT)).replace("\\", "/"),
            "showroom_html": (
                "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
                "public_showroom_meaning_topology_graph_v1.html"
            ),
        },
        "boundary_ack": "L1-A inference graph viz — structural router only; NOT prophecy·Track A.",
    }
    COMPLETION_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"quality_ok": quality_ok, "out": str(COMPLETION_OUT)}, ensure_ascii=False))
    return 0 if quality_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
