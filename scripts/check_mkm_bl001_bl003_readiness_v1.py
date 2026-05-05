#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check BL-001~003 readiness from latest artifacts.")
    ap.add_argument("--kpi-json", default="docs/final/artifacts/mkm_trackc_watch_exit_kpi_contract_latest.json")
    ap.add_argument("--decision-context-json", default="docs/final/artifacts/mkm_trackc_decision_context_latest.json")
    ap.add_argument("--hypo-fact-json", default="docs/final/artifacts/mkm_hypo_fact_promotion_status_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/mkm_bl001_bl003_readiness_latest.json")
    args = ap.parse_args()

    p_kpi = resolve(args.kpi_json)
    p_ctx = resolve(args.decision_context_json)
    p_hf = resolve(args.hypo_fact_json)
    out_path = resolve(args.output_json)

    checks = {
        "bl001_kpi_contract_exists": p_kpi.is_file(),
        "bl002_decision_context_exists": p_ctx.is_file(),
        "bl003_hypo_fact_status_exists": p_hf.is_file(),
    }

    if checks["bl001_kpi_contract_exists"]:
        kpi = load_json(p_kpi)
        checks["bl001_schema_ok"] = kpi.get("schema") == "mkm_trackc_watch_exit_kpi_contract_v1"
    else:
        checks["bl001_schema_ok"] = False

    if checks["bl002_decision_context_exists"]:
        ctx = load_json(p_ctx)
        checks["bl002_schema_ok"] = ctx.get("schema") == "mkm_trackc_decision_context_v1"
    else:
        checks["bl002_schema_ok"] = False

    if checks["bl003_hypo_fact_status_exists"]:
        hf = load_json(p_hf)
        checks["bl003_ready"] = hf.get("status") == "READY_FOR_QUEUE_IMPLEMENTATION"
    else:
        checks["bl003_ready"] = False

    all_pass = all(checks.values())
    payload = {
        "schema": "mkm_bl001_bl003_readiness_v1",
        "generated_at_utc": utc_now(),
        "checks": checks,
        "overall_status": "PASS" if all_pass else "HOLD",
        "next_action": (
            "Start BL-004/005 implementation"
            if all_pass
            else "Run missing builders and fix failing checks"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
