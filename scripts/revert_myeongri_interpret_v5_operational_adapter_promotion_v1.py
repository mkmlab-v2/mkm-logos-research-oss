#!/usr/bin/env python3
"""Revert harness recommended_operational_* from v5 back to archived v4 baseline (ops sign-off)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v5_operational_adapter_revert_latest.json"
V4_EVAL = "reports/myeongri_interpret_lora_v4_eval_locked100_guard448_latest.json"
V4_PREDS = "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
V4_DIV = "reports/myeongri_interpret_v4_diversity_audit_locked100_guard448_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--commander-ops-signoff",
        action="store_true",
        help="Required to write harness (or env MKM_INTERPRET_V5_OPS_REVERT=1).",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    signoff = args.commander_ops_signoff or _truthy_env("MKM_INTERPRET_V5_OPS_REVERT")
    if not args.status_json.is_file():
        print(json.dumps({"ok": False, "error": "missing harness status"}))
        return 2

    status = json.loads(args.status_json.read_text(encoding="utf-8"))
    promo = status.get("operational_adapter_promotion_v5") or {}
    if promo.get("status") != "active":
        print(json.dumps({"ok": False, "error": "v5 ops promotion not active"}))
        return 3

    baseline = (status.get("v4_variant_sft") or {}).get("operational_baseline_v4") or {}
    adapter = baseline.get("recommended_operational_adapter")
    if not adapter:
        adapter = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v4_variant_s100"

    before = {
        "recommended_operational_adapter": status.get("recommended_operational_adapter"),
        "recommended_operational_eval": status.get("recommended_operational_eval"),
    }
    after = {
        "recommended_operational_adapter": adapter,
        "recommended_operational_eval": baseline.get("recommended_operational_eval") or V4_EVAL,
        "recommended_operational_preds_jsonl": V4_PREDS,
        "recommended_operational_diversity_audit": V4_DIV,
    }

    plan = {
        "schema": "myeongri_interpret_v5_operational_adapter_revert_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "dry_run": bool(args.dry_run or not signoff),
        "commander_ops_signoff": signoff,
        "before": before,
        "after": after,
        "track_wall": {
            "track_a_live_auto_merge": False,
            "live_trading_trigger": False,
        },
    }

    if args.dry_run or not signoff:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": True,
                    "applied": False,
                    "reason": "dry_run" if args.dry_run else "commander_ops_signoff_required",
                    "plan": _rel(args.out_json),
                },
                ensure_ascii=False,
            )
        )
        return 0

    now = _utc_now()
    status["recommended_operational_adapter"] = after["recommended_operational_adapter"]
    status["recommended_operational_eval"] = after["recommended_operational_eval"]
    status["recommended_operational_preds_jsonl"] = after["recommended_operational_preds_jsonl"]
    status["recommended_operational_diversity_audit"] = after["recommended_operational_diversity_audit"]
    status["operational_adapter_promotion_v5"] = {
        **promo,
        "status": "reverted",
        "reverted_at_utc": now,
        "reverted_by": "commander_ops_signoff",
        "revert_report": _rel(args.out_json),
    }
    status["generated_at_utc"] = now
    args.status_json.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan["applied_at_utc"] = now
    plan["applied"] = True
    args.out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "applied": True, "adapter": adapter, "report": _rel(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
