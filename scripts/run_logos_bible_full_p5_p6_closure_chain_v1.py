#!/usr/bin/env python3
"""P5+P6 closure chain for Logos bible_full (B-track · research_only).

  py scripts/run_logos_bible_full_p5_p6_closure_chain_v1.py
  py scripts/run_logos_bible_full_p5_p6_closure_chain_v1.py --skip-krv-backfill
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
PY = sys.executable
OUT = ROOT / "reports/logos_bible_full_p5_p6_closure_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 7200) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(tail) > 1200:
        tail = tail[-1200:]
    return {"step": name, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-krv-backfill", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_krv_backfill:
        steps.append(_run("krv_gap_backfill_chapters", [PY, "scripts/backfill_logos_krv_corpus_gaps_v1.py"], timeout=7200))
        steps.append(_run("krv_citation_shard", [PY, "scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py"]))

    steps.extend(
        [
            _run("lemma_edges_expanded", [PY, "scripts/build_logos_lemma_verse_edges_v1.py", "--graph-max-edges", "500"]),
            _run("bloom_31k_secondary_fetch", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]),
            _run("dynamic_subgraph_router_sidecar", [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"]),
            _run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]),
            _run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ]
    )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_p5_p6",
                [PY, "-m", "pytest", "tests/test_logos_studio_31k_bloom_p5_p6_v1.py", "-q"],
                timeout=300,
            )
        )

    failed = [s["step"] for s in steps if not s.get("ok")]
    doc = {
        "schema": "logos_bible_full_p5_p6_closure_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(failed) == 0,
        "failed_steps": failed,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_p5_p6_closure_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
