#!/usr/bin/env python3
"""Phase 1 chain: lemma-verse edges + corpus split gate + router smoke ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_ol_graph_bridge_phase1_chain_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
ROUTER_OUT = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"


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
    ap.add_argument("--skip-phase0-parallel", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ok = True

    if not args.skip_phase0_parallel:
        ps = ROOT / "scripts" / "Run-LogosOlGraphBridgeParallel_v1.ps1"
        if ps.is_file():
            s = _run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps),
                ],
                timeout=600,
            )
            steps.append({"step": "phase0_parallel", **s})
            ok = ok and s["exit_code"] == 0

    for label, cmd in [
        (
            "lemma_edges",
            [
                sys.executable,
                str(ROOT / "scripts/build_logos_lemma_verse_edges_v1.py"),
                "--registry-json",
                str(REGISTRY),
            ],
        ),
        (
            "corpus_bundle",
            [sys.executable, str(ROOT / "scripts/build_logos_corpus_graph_bundle_v1.py")],
        ),
        (
            "corpus_split",
            [sys.executable, str(ROOT / "scripts/check_logos_lemma_verse_edges_corpus_split_v1.py")],
        ),
        (
            "subgraph_router_smoke",
            [
                sys.executable,
                str(ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"),
                "--query-id",
                "q01",
                "--output-json",
                str(ROUTER_OUT),
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
                "tests/test_build_logos_lemma_verse_edges_v1.py",
                "tests/test_logos_concept_bridge_v1.py",
                "tests/test_logos_corpus_graph_bundle_v1.py",
                "-q",
            ],
            timeout=300,
        )
        steps.append({"step": "pytest", **s})
        pytest_exit = s["exit_code"]
        ok = ok and pytest_exit == 0

    manifest_path = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
    lemma_manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    split_path = ROOT / "reports/logos_lemma_verse_edges_corpus_split_v1_latest.json"
    split_doc = json.loads(split_path.read_text(encoding="utf-8")) if split_path.is_file() else {}

    report = {
        "schema": "logos_ol_graph_bridge_phase1_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ok": ok,
        "lemma_edge_count": lemma_manifest.get("edge_count"),
        "corpus_split_gate_pass": split_doc.get("gate_pass"),
        "pytest_exit_code": pytest_exit,
        "steps": steps,
        "reproduce": "py scripts/run_logos_ol_graph_bridge_phase1_chain_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json), "lemma_edge_count": lemma_manifest.get("edge_count")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
