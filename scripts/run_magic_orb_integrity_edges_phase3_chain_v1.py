#!/usr/bin/env python3
"""Phase 3: integrity-colored edges — annotate blooms + regen artifacts + pytest."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/magic_orb_integrity_edges_phase3_chain_v1_latest.json"
HERO_CHAIN = ROOT / "scripts/run_bible_topology_hero_phase1_chain_v1.py"
PHASE2_CHAIN = ROOT / "scripts/run_magic_orb_router_bloom_phase2_chain_v1.py"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "magic_orb_integrity_edges_phase3_chain_v1",
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
        "pytest_integrity",
        [sys.executable, "-m", "pytest", "tests/test_magic_orb_graph_bloom_integrity_v1.py", "-q"],
    )
    ok = run_step("hero_slices_rebuild", [sys.executable, str(HERO_CHAIN)]) and ok
    report["hero_integrity_tiers"] = []
    hero_path = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_hero_slices_v1.json"
    if hero_path.is_file():
        bundle = json.loads(hero_path.read_text(encoding="utf-8-sig"))
        tiers: set[str] = set()
        for sl in bundle.get("slices") or []:
            for e in (sl.get("graph_bloom") or {}).get("edges") or []:
                if e.get("integrity_tier"):
                    tiers.add(str(e["integrity_tier"]))
        report["hero_integrity_tiers"] = sorted(tiers)
        ok = ok and len(tiers) >= 2
    ok = run_step(
        "q01_insight_regen",
        [
            sys.executable,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            "위기 가운데 언약의 안정과 신실",
            "--query-id",
            "q01",
            "--sync-public",
            "--skip-ann-lite",
        ],
    ) and ok
    ok = run_step(
        "pytest_bloom_smoke",
        [sys.executable, "-m", "pytest", "tests/test_build_magic_orb_graph_bloom_v1.py", "-q"],
    ) and ok

    tiers: set[str] = set()
    if INSIGHT.is_file():
        doc = json.loads(INSIGHT.read_text(encoding="utf-8-sig"))
        bloom = doc.get("graph_bloom") or {}
        for e in bloom.get("edges") or []:
            if e.get("integrity_tier"):
                tiers.add(str(e["integrity_tier"]))
        report["insight_bloom_nodes"] = len(bloom.get("nodes") or [])
        report["integrity_tiers"] = sorted(tiers)
        report["edge_integrity_policy"] = (bloom.get("edge_integrity_policy") or {}).get("schema")

    report["ok"] = ok and len(tiers) >= 1
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "tiers": sorted(tiers)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
