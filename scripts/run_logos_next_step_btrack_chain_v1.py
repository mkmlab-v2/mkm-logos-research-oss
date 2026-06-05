#!/usr/bin/env python3
"""Next-step Logos B-track: q09 RAG fix · risk_off crosswalk · Dan.2 trial [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_next_step_btrack_chain_v1_latest.json"


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
        _run("build_logos_lemma_verse_edges_v1.py", "lemma_edges_registry", [
            "--registry-json",
            "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
        ]),
        _run("build_logos_graphrag_empire_transition_dan2_trial_v1.py", "dan2_trial"),
        _run("build_kospi_june2026_logos_anchor_crosswalk_v1.py", "crosswalk"),
        _run("materialize_logos_gold_q09_election_router_ann_v1.py", "materialize_q09"),
        _run("materialize_logos_gold_crosswalk_queries_v1.py", "materialize_crosswalk_q10_q12"),
        _run(
            "materialize_logos_gold_router_canonical_v1.py",
            "router_canonical_q02_q05",
            ["--query-id", "q02", "--query-id", "q05", "--promote-gold-prefix-first"],
        ),
        _run("build_logos_gold_query_eval_report_v1.py", "gold_eval"),
        _run("render_kospi_june_4ai_prophecy_report_v1.py", "kospi_report"),
        _run("build_logos_exploration_insight_digest_v1.py", "insight_digest"),
        _run("run_logos_kospi_parallel_btrack_chain_v1.py", "parallel_btrack"),
    ]

    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    q09 = next((r for r in gold.get("rows") or [] if r.get("id") == "q09"), {})
    q10 = next((r for r in gold.get("rows") or [] if r.get("id") == "q10"), {})
    q11 = next((r for r in gold.get("rows") or [] if r.get("id") == "q11"), {})
    crosswalk = json.loads(
        (ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    dan2 = json.loads(
        (ROOT / "reports/logos_empire_transition_dan2_trial_audit_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    topic_ids = {a.get("topic_id") for a in crosswalk.get("anchors") or []}
    rag_hits = (q09.get("rag_fusion") or {}).get("gold_hits") or []

    ok = (
        all(s["exit_code"] == 0 for s in steps)
        and bool((gold.get("summary") or {}).get("gold_required_all_pass"))
        and q09.get("gate_pass") is True
        and q10.get("gate_pass") is True
        and q11.get("gate_pass") is True
        and len(rag_hits) >= 1
        and "risk_off_overnight" in topic_ids
        and dan2.get("topic_pass") is True
    )

    doc = {
        "schema": "logos_next_step_btrack_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": "HOLD_EXPLORATION",
        "ok": ok,
        "steps": steps,
        "results": {
            "gold_required_all_pass": (gold.get("summary") or {}).get("gold_required_all_pass"),
            "q09_gate_pass": q09.get("gate_pass"),
            "q10_gate_pass": q10.get("gate_pass"),
            "q11_gate_pass": q11.get("gate_pass"),
            "q09_rag_gold_hits": rag_hits,
            "crosswalk_topics": sorted(topic_ids),
            "dan2_trial_pass": dan2.get("topic_pass"),
            "dan2_seed_hits": f"{dan2.get('seed_hit_count')}/2",
        },
        "pointers": {
            "crosswalk": "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json",
            "gold_eval": "reports/logos_gold_query_eval_v1_latest.json",
            "dan2_trial": "reports/logos_graphrag_2026_empire_transition_dan2_trial_v1_latest.json",
            "dan2_audit": "reports/logos_empire_transition_dan2_trial_audit_v1_latest.json",
        },
    }
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "q09_rag_hits": len(rag_hits), "crosswalk_topics": len(topic_ids), "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
