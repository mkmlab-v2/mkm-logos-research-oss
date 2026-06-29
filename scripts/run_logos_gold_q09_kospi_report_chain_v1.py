#!/usr/bin/env python3
"""Chain: q09 election gold materialize → eval → KOSPI report render."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_gold_q09_kospi_report_chain_v1_latest.json"


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
    return {"step": step, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-1500:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps = [
        _run("build_kospi_june2026_logos_anchor_crosswalk_v1.py", "crosswalk"),
        _run("materialize_logos_gold_q09_election_router_ann_v1.py", "materialize_q09"),
        _run("build_logos_gold_query_eval_report_v1.py", "gold_eval"),
        _run("render_kospi_june_4ai_prophecy_report_v1.py", "kospi_report"),
        _run("build_logos_exploration_insight_digest_v1.py", "insight_digest"),
    ]

    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    q09 = next((r for r in gold.get("rows") or [] if r.get("id") == "q09"), {})
    doc_path = ROOT / "reports/kospi_june2026_prophecy_document_v1.md"
    doc_has_crosswalk = "2.5 Logos 앵커 crosswalk" in doc_path.read_text(encoding="utf-8-sig") if doc_path.is_file() else False

    ok = (
        all(s["exit_code"] == 0 for s in steps)
        and bool((gold.get("summary") or {}).get("gold_required_all_pass"))
        and q09.get("gate_pass") is True
        and doc_has_crosswalk
    )
    doc = {
        "schema": "logos_gold_q09_kospi_report_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "steps": steps,
        "gold_items": (gold.get("summary") or {}).get("items_evaluated"),
        "gold_required_all_pass": (gold.get("summary") or {}).get("gold_required_all_pass"),
        "q09_gate_pass": q09.get("gate_pass"),
        "kospi_doc_crosswalk_section": doc_has_crosswalk,
        "pointers": {
            "gold_eval": "reports/logos_gold_query_eval_v1_latest.json",
            "kospi_doc": "reports/kospi_june2026_prophecy_document_v1.md",
            "router_q09": "reports/magic_orb_insight_by_query/router_q09_latest.json",
        },
    }
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "q09_gate_pass": q09.get("gate_pass"), "gold_pass": doc["gold_required_all_pass"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
