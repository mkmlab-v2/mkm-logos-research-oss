#!/usr/bin/env python3
"""Chain: 31k corpus sasang routing overlay + gate + graph bundle (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/sasang_routing_sidecar_corpus_31k_chain_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_manifest_v1_latest.json"
GATE = ROOT / "reports/sasang_routing_sidecar_corpus_31k_gate_v1_latest.json"
GRAPH = ROOT / "docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    return cp.returncode, tail[-1] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="smoke: first N verses")
    ap.add_argument("--skip-graph", action="store_true")
    ap.add_argument("--skip-milestone", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    ok = True

    build_cmd = [sys.executable, "scripts/build_sasang_routing_sidecar_corpus_31k_v1.py"]
    if args.limit is not None:
        build_cmd.extend(["--limit", str(args.limit)])
    code, tail = _run(build_cmd)
    steps.append({"step": "corpus_build", "exit_code": code, "tail": tail})
    ok = ok and code == 0

    gate_cmd = [sys.executable, "scripts/check_sasang_routing_sidecar_corpus_31k_v1.py"]
    if args.limit is not None:
        gate_cmd.append("--allow-partial")
    code, tail = _run(gate_cmd)
    steps.append({"step": "corpus_gate", "exit_code": code, "tail": tail})
    ok = ok and code == 0

    if not args.skip_graph:
        code, tail = _run([sys.executable, "scripts/build_logos_corpus_sasang_routing_graph_bundle_v1.py"])
        steps.append({"step": "graph_bundle", "exit_code": code, "tail": tail})
        ok = ok and code == 0

    if not args.skip_milestone:
        code, tail = _run([sys.executable, "scripts/build_sasang_dynamics_btrack_milestone_v1.py"])
        steps.append({"step": "milestone_refresh", "exit_code": code, "tail": tail})
        ok = ok and code == 0

    doc = {
        "schema": "sasang_routing_sidecar_corpus_31k_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "all_ok": ok,
        "send_gate": "HOLD",
        "research_only": True,
        "track_a_blocked": True,
        "artifacts": {
            "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "gate": str(GATE.relative_to(ROOT)).replace("\\", "/"),
            **(
                {"graph_bundle": str(GRAPH.relative_to(ROOT)).replace("\\", "/")}
                if not args.skip_graph
                else {}
            ),
        },
        "steps": steps,
        "reproduce": "py scripts/run_sasang_routing_sidecar_corpus_31k_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "all_ok": ok, "out": str(OUT)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
