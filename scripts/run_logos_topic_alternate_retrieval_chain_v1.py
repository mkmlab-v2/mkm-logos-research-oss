#!/usr/bin/env python3
"""Parallel alternate retrieval audits: GraphRAG + typology + lemma vs 4D centroid."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_topic_alternate_retrieval_chain_v1_latest.json"


def _run(script: str, step: str, extra: list[str] | None = None) -> dict:
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return {"step": step, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-1200:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps = [
        _run("audit_logos_topic_graphrag_seed_retrieval_v1.py", "graphrag"),
        _run("audit_logos_topic_typology_seed_retrieval_v1.py", "typology"),
        _run("audit_logos_topic_lemma_edge_seed_retrieval_v1.py", "lemma_edges"),
        _run("compare_logos_4d_vs_alternate_retrieval_v1.py", "compare"),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)
    compare_path = ROOT / "reports/logos_4d_vs_alternate_retrieval_v1_latest.json"
    compare = json.loads(compare_path.read_text(encoding="utf-8-sig")) if compare_path.is_file() else {}

    doc = {
        "schema": "logos_topic_alternate_retrieval_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "steps": steps,
        "compare_pointer": "reports/logos_4d_vs_alternate_retrieval_v1_latest.json",
        "channels": compare.get("channels") or {},
        "routing_recommendation": compare.get("routing_recommendation"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "channels": doc["channels"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
