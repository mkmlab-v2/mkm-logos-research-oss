#!/usr/bin/env python3
"""Parallel B-track chain: KOSPI×Logos crosswalk + insight digest + 4D monitor."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_kospi_parallel_btrack_chain_v1_latest.json"

PHASE1_JOBS = [
    ("kospi_logos_crosswalk", [PY, str(ROOT / "scripts/build_kospi_june2026_logos_anchor_crosswalk_v1.py")]),
    ("logos_4d_monitor", [PY, str(ROOT / "scripts/refresh_logos_4d_monitoring_snapshot_v1.py")]),
    ("graphrag_audit", [PY, str(ROOT / "scripts/audit_logos_topic_graphrag_seed_retrieval_v1.py")]),
    ("gold_eval", [PY, str(ROOT / "scripts/build_logos_gold_query_eval_report_v1.py")]),
]
PHASE2_JOBS = [
    ("logos_insight_digest", [PY, str(ROOT / "scripts/build_logos_exploration_insight_digest_v1.py")]),
]


def _run(name: str, cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return {"step": name, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-1500:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--sequential", action="store_true", help="Run jobs one-by-one (debug).")
    args = ap.parse_args()

    steps: list[dict] = []

    def _run_batch(jobs: list[tuple[str, list[str]]], *, parallel: bool) -> None:
        if parallel:
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                futures = [pool.submit(_run, name, cmd) for name, cmd in jobs]
                batch = [f.result() for f in futures]
            batch.sort(key=lambda s: [n for n, _ in jobs].index(s["step"]))
            steps.extend(batch)
        else:
            for name, cmd in jobs:
                steps.append(_run(name, cmd))

    parallel = not args.sequential
    _run_batch(PHASE1_JOBS, parallel=parallel)
    _run_batch(PHASE2_JOBS, parallel=False)

    crosswalk = json.loads((ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json").read_text(encoding="utf-8-sig"))
    digest = json.loads((ROOT / "reports/logos_exploration_insight_digest_v1_latest.json").read_text(encoding="utf-8-sig"))
    monitor = json.loads((ROOT / "reports/logos_4d_monitoring_snapshot_v1_latest.json").read_text(encoding="utf-8-sig"))
    graphrag = json.loads((ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json").read_text(encoding="utf-8-sig"))
    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))

    ok = all(s["exit_code"] == 0 for s in steps)
    doc = {
        "schema": "logos_kospi_parallel_btrack_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "final_action": "HOLD_EXPLORATION",
        "parallel": not args.sequential,
        "steps": steps,
        "summary": {
            "kospi_primary_logos_topic": (crosswalk.get("summary") or {}).get("primary_topic"),
            "kospi_topics_linked": (crosswalk.get("summary") or {}).get("topics_linked"),
            "insight_final_action": digest.get("final_action"),
            "graphrag_seed_hits": (graphrag.get("summary") or {}).get("seed_hits"),
            "gold_pass": (gold.get("summary") or {}).get("gold_required_all_pass"),
            "4d_monitor_policy_ok": monitor.get("policy_check_ok"),
            "organic_4d_spike": monitor.get("organic_4d_topic_spike"),
        },
        "pointers": {
            "crosswalk": "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json",
            "insight_digest": "reports/logos_exploration_insight_digest_v1_latest.json",
            "4d_monitor": "reports/logos_4d_monitoring_snapshot_v1_latest.json",
        },
    }
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
