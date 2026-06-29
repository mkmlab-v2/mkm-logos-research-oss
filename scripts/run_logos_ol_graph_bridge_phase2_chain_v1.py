#!/usr/bin/env python3
"""Phase 2 chain: concept_bridge registry + LLM governance + human gate queue ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_ol_graph_bridge_phase2_chain_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
GOVERNANCE = ROOT / "reports/logos_concept_bridge_governance_v1_latest.json"
QUEUE = ROOT / "docs/final/artifacts/logos_concept_bridge_human_gate_queue_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, timeout: int = 300) -> dict[str, Any]:
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
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ok = True

    for label, cmd in [
        (
            "llm_plan",
            [sys.executable, str(ROOT / "scripts/build_logos_concept_bridge_llm_plan_v1.py")],
        ),
        (
            "concept_bridge_registry",
            [sys.executable, str(ROOT / "scripts/build_logos_concept_bridge_registry_v1.py")],
        ),
        (
            "governance_gate",
            [sys.executable, str(ROOT / "scripts/check_logos_concept_bridge_governance_v1.py")],
        ),
        (
            "human_gate_queue",
            [
                sys.executable,
                str(ROOT / "scripts/build_logos_concept_bridge_human_gate_queue_v1.py"),
                "--wave",
                "1",
            ],
        ),
        (
            "alignment",
            [sys.executable, str(ROOT / "scripts/build_logos_ol_graph_bridge_alignment_v1.py")],
        ),
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
                "tests/test_build_logos_concept_bridge_registry_v1.py",
                "tests/test_build_logos_concept_bridge_human_gate_queue_v1.py",
                "tests/test_logos_concept_bridge_v1.py",
                "-q",
            ],
            timeout=300,
        )
        steps.append({"step": "pytest", **s})
        pytest_exit = s["exit_code"]
        ok = ok and pytest_exit == 0

    registry_doc = json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.is_file() else {}
    governance_doc = json.loads(GOVERNANCE.read_text(encoding="utf-8")) if GOVERNANCE.is_file() else {}
    queue_doc = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.is_file() else {}
    alignment_path = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"
    alignment_doc = (
        json.loads(alignment_path.read_text(encoding="utf-8")) if alignment_path.is_file() else {}
    )

    report = {
        "schema": "logos_ol_graph_bridge_phase2_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ok": ok,
        "human_reviewed_ratio": registry_doc.get("human_reviewed_ratio"),
        "llm_bridge_count": governance_doc.get("llm_bridge_count"),
        "governance_gate_pass": governance_doc.get("gate_pass"),
        "human_gate_pending_count": queue_doc.get("queue_count"),
        "phase2_complete": alignment_doc.get("phase2_complete"),
        "pytest_exit_code": pytest_exit,
        "steps": steps,
        "reproduce": "py scripts/run_logos_ol_graph_bridge_phase2_chain_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out_json),
                "human_reviewed_ratio": registry_doc.get("human_reviewed_ratio"),
                "governance_gate_pass": governance_doc.get("gate_pass"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
