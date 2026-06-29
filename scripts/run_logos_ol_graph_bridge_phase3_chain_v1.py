#!/usr/bin/env python3
"""Phase 3 chain: subgraph replay + router + showroom audit slice + v6 panel + alignment ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_ol_graph_bridge_phase3_chain_v1_latest.json"
ROUTER_OUT = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
SLICE_GATE = ROOT / "reports/showroom_logos_subgraph_audit_slice_gate_v1_latest.json"
PANEL_GATE = ROOT / "reports/logos_showroom_v6_subgraph_audit_panel_gate_v1_latest.json"
REPLAY_PS1 = ROOT / "scripts/Invoke-LogosSubgraphReplayBatch_v1.ps1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-id", default="q01")
    ap.add_argument("--skip-replay-batch", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ok = True

    if not args.skip_replay_batch:
        s = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPLAY_PS1),
            ],
            timeout=900,
        )
        steps.append({"step": "subgraph_replay_batch", **s})
        ok = ok and s["exit_code"] == 0

    for label, cmd in [
        ("wire_poc_showroom", [sys.executable, str(ROOT / "scripts/build_mkm_graph_wire_rag_poc_v1.py")]),
        (
            "subgraph_router",
            [
                sys.executable,
                str(ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"),
                "--query-id",
                args.query_id,
                "--output-json",
                str(ROUTER_OUT),
            ],
        ),
        ("showroom_audit_slice", [sys.executable, str(ROOT / "scripts/build_showroom_logos_subgraph_audit_slice_v1.py")]),
        ("showroom_audit_slice_gate", [sys.executable, str(ROOT / "scripts/check_showroom_logos_subgraph_audit_slice_v1.py")]),
        ("showroom_v6_audit_panel", [sys.executable, str(ROOT / "scripts/build_logos_showroom_v6_subgraph_audit_panel_v1.py")]),
        ("showroom_v6_audit_panel_gate", [sys.executable, str(ROOT / "scripts/check_logos_showroom_v6_subgraph_audit_panel_v1.py")]),
        ("alignment", [sys.executable, str(ROOT / "scripts/build_logos_ol_graph_bridge_alignment_v1.py")]),
    ]:
        s = _run(cmd)
        steps.append({"step": label, **s})
        ok = ok and s["exit_code"] == 0

    pytest_exit: int | None = None
    if ok and not args.skip_pytest:
        s = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_ol_graph_bridge_phase3_chain_v1.py",
                "tests/test_build_showroom_logos_subgraph_audit_slice_v1.py",
                "-q",
                "-k",
                "not test_logos_ol_graph_bridge_phase3_chain_smoke",
            ],
            timeout=300,
        )
        steps.append({"step": "pytest", **s})
        pytest_exit = s["exit_code"]
        ok = ok and pytest_exit == 0

    router_doc = json.loads(ROUTER_OUT.read_text(encoding="utf-8")) if ROUTER_OUT.is_file() else {}
    slice_gate_doc = json.loads(SLICE_GATE.read_text(encoding="utf-8")) if SLICE_GATE.is_file() else {}
    panel_gate_doc = json.loads(PANEL_GATE.read_text(encoding="utf-8")) if PANEL_GATE.is_file() else {}
    alignment_path = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"
    alignment_doc = (
        json.loads(alignment_path.read_text(encoding="utf-8")) if alignment_path.is_file() else {}
    )

    report = {
        "schema": "logos_ol_graph_bridge_phase3_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "ok": ok,
        "query_id": args.query_id,
        "router_path_count": len(router_doc.get("paths") or []),
        "showroom_audit_slice_gate_pass": slice_gate_doc.get("gate_pass"),
        "showroom_audit_panel_gate_pass": panel_gate_doc.get("gate_pass"),
        "phase3_complete": alignment_doc.get("phase3_complete"),
        "pytest_exit_code": pytest_exit,
        "steps": steps,
        "reproduce": "py scripts/run_logos_ol_graph_bridge_phase3_chain_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out_json),
                "showroom_audit_slice_gate_pass": slice_gate_doc.get("gate_pass"),
                "showroom_audit_panel_gate_pass": panel_gate_doc.get("gate_pass"),
                "phase3_complete": alignment_doc.get("phase3_complete"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
