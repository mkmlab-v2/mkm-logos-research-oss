#!/usr/bin/env python3
"""Promote Luke path → verify GraphRAG 18/18 + gap triage zero + gold eval."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_regime_watch_luke_promotion_verify_v1_latest.json"


def _run(cmd: list[str], step: str) -> dict:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return {"step": step, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-promote", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_promote:
        steps.append(_run([PY, str(ROOT / "scripts/promote_logos_graphrag_regime_watch_luke_signoff_v1.py")], "promote"))
    steps.extend(
        [
            _run([PY, str(ROOT / "scripts/audit_logos_topic_graphrag_seed_retrieval_v1.py")], "graphrag_audit"),
            _run([PY, str(ROOT / "scripts/audit_logos_graphrag_seed_gap_triage_v1.py")], "gap_triage"),
            _run([PY, str(ROOT / "scripts/build_logos_gold_query_eval_report_v1.py")], "gold_eval"),
        ]
    )

    audit = json.loads((ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json").read_text(encoding="utf-8-sig"))
    triage = json.loads((ROOT / "reports/logos_graphrag_seed_gap_triage_v1_latest.json").read_text(encoding="utf-8-sig"))
    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    target = json.loads((ROOT / "reports/logos_graphrag_2026_regime_watch_latest.json").read_text(encoding="utf-8-sig"))

    audit_summary = audit.get("summary") or {}
    triage_summary = triage.get("summary") or {}
    graphrag_ok = audit_summary.get("seed_hits") == "18/18" and audit_summary.get("topic_hits") == "6/6"
    gap_ok = triage_summary.get("gap_count") == 0
    gold_ok = bool((gold.get("summary") or {}).get("gold_required_all_pass"))
    luke_ok = "vr_luke_22_4" in json.dumps(target)
    promoted = bool(target.get("promotion_signoff"))

    ok = all(s["exit_code"] == 0 for s in steps) and graphrag_ok and gap_ok and gold_ok and luke_ok and promoted
    doc = {
        "schema": "logos_regime_watch_luke_promotion_verify_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "final_action": "HOLD_EXPLORATION",
        "steps": steps,
        "graphrag_seed_hits": audit_summary.get("seed_hits"),
        "graphrag_topic_hits": audit_summary.get("topic_hits"),
        "gap_count": triage_summary.get("gap_count"),
        "gold_required_all_pass": gold_ok,
        "luke_promoted": luke_ok,
        "promotion_signoff_present": promoted,
        "pointers": {
            "target": "reports/logos_graphrag_2026_regime_watch_latest.json",
            "signoff": "reports/logos_graphrag_regime_watch_luke_promotion_signoff_v1_latest.json",
        },
    }
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "seed_hits": audit_summary.get("seed_hits"), "gap_count": triage_summary.get("gap_count"), "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
