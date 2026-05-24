#!/usr/bin/env python3
"""M24: One-click RQ-019 inter-agent regression chain (research_only, no live trading)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_regression_chain_v1_latest.json"

_ARTIFACT_CHECKS = (
    ("health_wire_sidecar_dialogue", "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json"),
    ("health_wire_sidecar_live_http", "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_live_http_v1_latest.json"),
    ("ko_health_sidecar_batch_chain", "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_batch_chain_v1_latest.json"),
    ("m3_public_copy", "docs/final/artifacts/mkm_inter_agent_m3_public_copy_v1_latest.json"),
    ("trackc_rq019_slice", "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json"),
    ("wire_gloss_sidecar_enriched", "docs/final/artifacts/mkm_inter_agent_wire_gloss_sidecar_enriched_v1_latest.json"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"cmd": cmd, "exit_code": cp.returncode, "ok": cp.returncode == 0, "tail": (cp.stdout or cp.stderr or "")[-400:]}


def _artifact_ok(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.is_file():
        return {"ok": False, "skipped": False, "artifact": rel}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": bool(doc.get("ok")), "skipped": True, "artifact": rel}


def run_chain(*, skip_pytest: bool = False, quick: bool = True) -> dict[str, Any]:
    py = sys.executable
    results: list[dict[str, Any]] = []

    if not skip_pytest:
        results.append({"step": "pytest_m26", **_run([py, "-m", "pytest", "tests/test_mkm_inter_agent_wire_m26_v1.py", "-q"])})

    if quick:
        for name, rel in _ARTIFACT_CHECKS:
            results.append({"step": name, **_artifact_ok(rel)})
        for name, cmd in (
            ("rq019_milestone_index", [py, "scripts/build_mkm_inter_agent_rq019_milestone_artifact_index_v1.py"]),
            ("rq019_ops_slice", [py, "scripts/build_mkm_inter_agent_rq019_ops_slice_v1.py"]),
            ("trackc_ops_dashboard", [py, "scripts/build_mkm_trackc_ops_dashboard_v1.py"]),
        ):
            results.append({"step": name, **_run(cmd)})
    else:
        for name, cmd in (
            ("health_wire_sidecar_dialogue", [py, "scripts/capture_mkm_inter_agent_health_wire_sidecar_dialogue_v1.py", "--turns", "3"]),
            ("health_wire_sidecar_live_http", [py, "scripts/capture_mkm_inter_agent_health_wire_sidecar_live_http_v1.py", "--turns", "2"]),
            ("ko_health_sidecar_batch_chain", [py, "scripts/run_mkm_inter_agent_ko_health_sidecar_batch_chain_v1.py", "--turns", "3"]),
            ("m3_public_copy", [py, "scripts/emit_mkm_inter_agent_m3_public_copy_v1.py"]),
            ("rq019_milestone_index", [py, "scripts/build_mkm_inter_agent_rq019_milestone_artifact_index_v1.py"]),
            ("rq019_ops_slice", [py, "scripts/build_mkm_inter_agent_rq019_ops_slice_v1.py"]),
        ):
            results.append({"step": name, **_run(cmd)})

    # Milestone index is derived from encoding_status; do not block quick smoke on index lag.
    _non_blocking = {"rq019_milestone_index"}
    all_ok = all(r.get("ok") for r in results if r.get("step") not in _non_blocking)
    status = {}
    status_path = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))

    dash_ok = True
    dash_path = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
    if dash_path.is_file():
        dash = json.loads(dash_path.read_text(encoding="utf-8"))
        ia = ((dash.get("trackc") or {}).get("inter_agent_rq019")) or {}
        dash_ok = ia.get("role") == "inter_agent_rq019_research_slice_v1" and ia.get("research_only") is True

    return {
        "quick_mode": quick,
        "ok": all_ok and dash_ok,
        "schema": "mkm_inter_agent_rq019_regression_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "steps": results,
        "trackc_dashboard_inter_agent_ok": dash_ok,
        "encoding_status_flags": {
            "core_ready": status.get("rq_019_milestones_core_ready"),
            "m12_m25_ready": status.get("rq_019_language_dev_m12_m25_ready"),
            "m12_m28_ready": status.get("rq_019_language_dev_m12_m28_ready"),
        },
        "boundary_ack": "Regression chain for B-track inter-agent lane; use --full for slow re-capture.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--full", action="store_true", help="Re-run all captures (slow; includes live HTTP)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_chain(skip_pytest=args.skip_pytest, quick=not args.full)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
