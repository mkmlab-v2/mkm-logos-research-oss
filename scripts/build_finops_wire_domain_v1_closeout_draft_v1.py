#!/usr/bin/env python3
"""FinOps wire domain v1 — L1 closeout draft (human approval required)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVAL = ROOT / "reports/finops_wire_domain_v1_eval_latest.json"
BENCH_V0 = ROOT / "reports/finops_wire_bench_v0_latest.json"
SCOPE = ROOT / "reports/finops_wire_domain_scope_v1_latest.md"
DEFAULT_OUT = ROOT / "reports/finops_wire_domain_v1_closeout_draft_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_closeout_draft() -> dict[str, Any]:
    ev = _read(EVAL)
    bench = _read(BENCH_V0)
    return {
        "ok": bool(ev.get("ok")),
        "schema": "finops_wire_domain_v1_closeout_draft_v1",
        "generated_at_utc": _utc(),
        "approval_status": "DRAFT_PENDING_COMMANDER",
        "domain_id": "finops_handoff_v1",
        "lane": "L1_skeleton",
        "parent_rq_019": "CLOSED",
        "branch_target": "b-track-finops-wire-v1",
        "operator_runbook": {
            "push_bundle": "py scripts/build_finops_wire_push_bundle_v1.py --run-export --run-gloss --run-regression --run-wire-bench",
            "domain_eval": "py scripts/run_finops_wire_domain_v1_eval_v1.py",
            "domain_chain": "py scripts/run_finops_wire_domain_v1_chain_v1.py",
            "weekly_smoke": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1",
        },
        "pointers": {
            "scope_md": SCOPE.relative_to(ROOT).as_posix(),
            "bench_v0": BENCH_V0.relative_to(ROOT).as_posix(),
            "domain_eval": EVAL.relative_to(ROOT).as_posix(),
            "holdout": "docs/final/artifacts/finops_wire_bench_holdout_v1_latest.json",
            "inventory": "reports/finops_wire_corpus_inventory_v1_latest.json",
        },
        "finops_kpis": bench.get("finops_kpis"),
        "domain_gates": ev.get("gates"),
        "disclaimer_ko": bench.get("disclaimer_ko")
        or "역복원 exact 약 57.9%; 무손실·100%·lingua franca 완성 미주장.",
        "boundary_ack": "Draft L1 closeout for FinOps wire v1 only; not Track A, live trading, or external send.",
        "human_gates_before_official": [
            "commander_approve_l1_closeout",
            "legal_before_external_send",
            "optional_pilot_customer_corpus",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_closeout_draft()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
