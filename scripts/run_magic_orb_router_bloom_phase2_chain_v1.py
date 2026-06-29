#!/usr/bin/env python3
"""Phase 2: router seed-chain + hero-slice bloom fallback → insight regen → validate."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/magic_orb_router_bloom_phase2_chain_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
BLOOM = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json"
DEFAULT_QUERY = "위기 가운데 언약의 안정과 신실"
DEFAULT_QUERY_ID = "q01"
MIN_BLOOM_VERSE_NODES = 4


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "magic_orb_router_bloom_phase2_chain_v1",
        "generated_at_utc": _utc(),
        "steps": [],
        "ok": False,
    }

    def run_step(name: str, cmd: list[str]) -> bool:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        step = {
            "name": name,
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()[:2000],
            "stderr": proc.stderr.strip()[:500],
        }
        report["steps"].append(step)
        return proc.returncode == 0

    ok = run_step(
        "pytest_bloom",
        [sys.executable, "-m", "pytest", "tests/test_build_magic_orb_graph_bloom_v1.py", "-q"],
    )

    ok = run_step(
        "rebuild_bloom_from_router",
        [
            sys.executable,
            str(ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"),
            "--query",
            DEFAULT_QUERY,
            "--router-json",
            str(ROUTER),
            "--out-json",
            str(BLOOM),
        ],
    ) and ok

    ok = run_step(
        "rebuild_insight",
        [
            sys.executable,
            str(ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"),
            "--query",
            DEFAULT_QUERY,
            "--query-id",
            DEFAULT_QUERY_ID,
            "--router-json",
            str(ROUTER),
            "--bloom-json",
            str(BLOOM),
            "--sync-public",
        ],
    ) and ok

    ok = run_step(
        "pytest_phase2",
        [sys.executable, "-m", "pytest", "tests/test_magic_orb_router_bloom_phase2_v1.py", "-q"],
    ) and ok

    bloom_nodes = bloom_edges = verse_nodes = None
    for path in (INSIGHT, BLOOM):
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            bloom = doc.get("graph_bloom") if path == INSIGHT else doc
            if isinstance(bloom, dict):
                nodes = bloom.get("nodes") or []
                bloom_nodes = len(nodes)
                bloom_edges = len(bloom.get("edges") or [])
                verse_nodes = sum(1 for n in nodes if n.get("kind") == "verse")
                break

    report["bloom_nodes"] = bloom_nodes
    report["bloom_edges"] = bloom_edges
    report["bloom_verse_nodes"] = verse_nodes
    report["public_synced"] = PUBLIC.is_file()
    report["ok"] = ok and (verse_nodes or 0) >= MIN_BLOOM_VERSE_NODES

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "bloom_nodes": bloom_nodes,
                "bloom_edges": bloom_edges,
                "verse_nodes": verse_nodes,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
