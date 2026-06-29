#!/usr/bin/env python3
"""Chain: Luke.22.4 graphrag patch verify → gold typology wiring eval."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PY = sys.executable
PATCHED = ROOT / "reports/logos_graphrag_2026_regime_watch_luke_patch_v1_latest.json"
OUT = ROOT / "reports/logos_luke_patch_gold_wiring_chain_v1_latest.json"


def _run(cmd: list[str], step: str) -> dict:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return {"step": step, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-1500:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps = [
        _run([PY, str(ROOT / "scripts/apply_logos_graphrag_regime_watch_luke_gap_patch_v1.py")], "luke_patch"),
        _run(
            [
                PY,
                str(ROOT / "scripts/audit_logos_topic_graphrag_seed_retrieval_v1.py"),
                "--out-json",
                str(ROOT / "reports/logos_topic_graphrag_seed_retrieval_patched_v1_latest.json"),
                "--graphrag-ref-overrides",
                str(ROOT / "reports/logos_graphrag_regime_watch_ref_override_v1.json"),
            ],
            "graphrag_audit_patched",
        ),
        _run([PY, str(ROOT / "scripts/build_logos_gold_typology_rerank_wiring_eval_v1.py")], "gold_wiring"),
        _run([PY, str(ROOT / "scripts/build_logos_gold_query_eval_report_v1.py")], "gold_eval_refresh"),
    ]

    patched_text = PATCHED.read_text(encoding="utf-8-sig") if PATCHED.is_file() else ""
    luke_ok = "vr_luke_22_4" in patched_text and "Luke.22.4" in patched_text

    patched_audit_path = ROOT / "reports/logos_topic_graphrag_seed_retrieval_patched_v1_latest.json"
    patched_audit = json.loads(patched_audit_path.read_text(encoding="utf-8-sig")) if patched_audit_path.is_file() else {}
    audit_summary = patched_audit.get("summary") or {}

    wiring = json.loads((ROOT / "reports/logos_gold_typology_rerank_wiring_v1_latest.json").read_text(encoding="utf-8-sig"))
    gold_eval = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    graphrag_18 = audit_summary.get("seed_hits") == "18/18"

    ok = all(s["exit_code"] == 0 for s in steps) and luke_ok and graphrag_18
    doc = {
        "schema": "logos_luke_patch_gold_wiring_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "steps": steps,
        "luke_patch_verified": luke_ok,
        "graphrag_seed_hits_patched": audit_summary.get("seed_hits"),
        "graphrag_topic_hits_patched": audit_summary.get("topic_hits"),
        "gold_typology_wiring": wiring.get("summary"),
        "gold_eval_pass": (gold_eval.get("summary") or {}).get("gold_required_all_pass"),
        "pointers": {
            "patched_graphrag": "reports/logos_graphrag_2026_regime_watch_luke_patch_v1_latest.json",
            "wiring_eval": "reports/logos_gold_typology_rerank_wiring_v1_latest.json",
            "wiring_contract": "docs/final/artifacts/logos_gold_typology_rerank_wiring_contract_v1.json",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "luke_patch_verified": luke_ok, "gold_pass": doc["gold_eval_pass"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
