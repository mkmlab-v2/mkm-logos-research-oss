#!/usr/bin/env python3
"""Chain: canonical graphrag re-audit → gap triage → typology ANN rerank PoC."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_graphrag_gap_typology_chain_v1_latest.json"


def _run(script: str, step: str) -> dict:
    cp = subprocess.run(
        [PY, str(ROOT / "scripts" / script)],
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
        _run("audit_logos_topic_graphrag_seed_retrieval_v1.py", "graphrag_canonical"),
        _run("audit_logos_graphrag_seed_gap_triage_v1.py", "gap_triage"),
        _run("build_logos_topic_typology_ann_rerank_poc_v1.py", "typology_ann_rerank"),
        _run("compare_logos_4d_vs_alternate_retrieval_v1.py", "compare_refresh"),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)

    graphrag = json.loads((ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json").read_text(encoding="utf-8-sig"))
    gap = json.loads((ROOT / "reports/logos_graphrag_seed_gap_triage_v1_latest.json").read_text(encoding="utf-8-sig"))
    rerank = json.loads((ROOT / "reports/logos_topic_typology_ann_rerank_poc_v1_latest.json").read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "logos_graphrag_gap_typology_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "steps": steps,
        "results": {
            "graphrag_seed_hits": graphrag.get("summary", {}).get("seed_hits"),
            "gap_triage": gap.get("summary"),
            "typology_ann_rerank": rerank.get("summary"),
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "results": doc["results"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
