#!/usr/bin/env python3
"""Promote harness recommended_operational_adapter v4→v5 (ops sign-off only, B-track interpret)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

V4_ADAPTER = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v4_variant_s100"
V5_ADAPTER = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v5_wording_sweep_s100"
V5_EVAL = "reports/myeongri_interpret_lora_v5_eval_locked100_guard448_latest.json"
V5_PREDS = "reports/myeongri_interpret_lora_v5_preds_locked100_guard448_latest.jsonl"
V5_DIV = "reports/myeongri_interpret_v5_diversity_audit_locked100_guard448_latest.json"
V5_CLOSURE = "reports/myeongri_interpret_v5_calibration30_closure_latest.json"
V5_READINESS = "reports/myeongri_interpret_v5_operational_promotion_readiness_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v5_operational_adapter_promotion_latest.json"
DEFAULT_RADAR = ROOT / "reports/mkm_evolution_radar_daily_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _validate_gates() -> list[str]:
    errors: list[str] = []
    adapter_dir = ROOT / V5_ADAPTER
    if not (adapter_dir / "adapter_config.json").is_file():
        errors.append(f"missing adapter_config: {V5_ADAPTER}")
    if not any(adapter_dir.glob("adapter_model*")):
        errors.append(f"missing adapter weights: {V5_ADAPTER}")

    closure_path = ROOT / V5_CLOSURE
    if not closure_path.is_file():
        errors.append("missing v5_calibration30_closure")
    else:
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        if closure.get("phase_status") != "closed":
            errors.append("v5_calibration30 not closed")
        if not closure.get("calibration_gate_pass"):
            errors.append("v5 calibration_gate_pass false")

    eval_path = ROOT / V5_EVAL
    if not eval_path.is_file():
        errors.append("missing v5 locked100 eval")
    else:
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        if ev.get("parse_ok_rate") != 1.0:
            errors.append("v5 parse_ok_rate != 1.0")
        if (ev.get("envelope_coerced_rate") or 1) > 0.15:
            errors.append("v5 envelope_coerced_rate > 0.15")

    div_path = ROOT / V5_DIV
    if not div_path.is_file():
        errors.append("missing v5 diversity audit")
    else:
        div = json.loads(div_path.read_text(encoding="utf-8"))
        if not div.get("narrative_diversity_gate_pass"):
            errors.append("v5 narrative_diversity_gate_pass false")
        if div.get("empty_insight_row_count", 1) != 0:
            errors.append("v5 empty_insight_row_count != 0")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--radar-json", type=Path, default=DEFAULT_RADAR)
    ap.add_argument(
        "--commander-ops-signoff",
        action="store_true",
        help="Required to write harness (or env MKM_INTERPRET_V5_OPS_SIGNOFF=1).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate gates only; no harness write.")
    ap.add_argument("--skip-radar-update", action="store_true")
    args = ap.parse_args()

    signoff = args.commander_ops_signoff or _truthy_env("MKM_INTERPRET_V5_OPS_SIGNOFF")
    errors = _validate_gates()
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 1

    if not args.status_json.is_file():
        print(json.dumps({"ok": False, "error": "missing harness status"}))
        return 2

    status = json.loads(args.status_json.read_text(encoding="utf-8"))
    before = {
        "recommended_operational_adapter": status.get("recommended_operational_adapter"),
        "recommended_operational_eval": status.get("recommended_operational_eval"),
    }

    plan = {
        "schema": "myeongri_interpret_v5_operational_adapter_promotion_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "dry_run": bool(args.dry_run or not signoff),
        "commander_ops_signoff": signoff,
        "before": before,
        "after": {
            "recommended_operational_adapter": V5_ADAPTER,
            "recommended_operational_eval": V5_EVAL,
            "recommended_operational_preds_jsonl": V5_PREDS,
            "recommended_operational_diversity_audit": V5_DIV,
        },
        "prior_operational_baseline_preserved": {
            "v4_adapter": V4_ADAPTER,
            "v4_eval": before.get("recommended_operational_eval"),
            "location": "v4_variant_sft.operational_baseline_v4",
        },
        "track_wall": {
            "track_a_live_auto_merge": False,
            "live_trading_trigger": False,
            "interpret_only_b_track": True,
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
    v4 = status.setdefault("v4_variant_sft", {})
    v4["operational_baseline_v4"] = {
        "archived_at_utc": now,
        "recommended_operational_adapter": before.get("recommended_operational_adapter"),
        "recommended_operational_eval": before.get("recommended_operational_eval"),
        "reason": "superseded_by_v5_ops_promotion",
    }
    status["recommended_operational_adapter"] = V5_ADAPTER
    status["recommended_operational_eval"] = V5_EVAL
    status["recommended_operational_preds_jsonl"] = V5_PREDS
    status["recommended_operational_diversity_audit"] = V5_DIV
    status["operational_adapter_promotion_v5"] = {
        "status": "active",
        "promoted_at_utc": now,
        "promoted_by": "commander_ops_signoff_2026-06-01",
        "source": "apply_myeongri_interpret_v5_operational_adapter_promotion_v1.py",
        "prior_adapter": before.get("recommended_operational_adapter"),
        "report": _rel(args.out_json),
        "interpretation_ko": "B-track interpret 운영 어댑터 v5. Track A·실매매 자동 승격 없음.",
    }
    status["generated_at_utc"] = now
    args.status_json.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan["applied_at_utc"] = now
    plan["applied"] = True
    args.out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readiness_path = ROOT / V5_READINESS
    if readiness_path.is_file():
        rd = json.loads(readiness_path.read_text(encoding="utf-8"))
        rd["swap_recommended"] = True
        rd["swap_applied_at_utc"] = now
        rd["current_operational_adapter"] = V5_ADAPTER
        readiness_path.write_text(json.dumps(rd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_radar_update and args.radar_json.is_file():
        doc = json.loads(args.radar_json.read_text(encoding="utf-8-sig"))
        for c in doc.get("candidates") or []:
            if str(c.get("id")) == "myeongri_interpret_v5_operational_adapter_promotion":
                c["approval_status"] = "approved"
                c["approved_at_utc"] = now
                c["approved_by"] = "commander_ops_signoff_2026-06-01"
                c["implementation_note"] = "harness recommended_operational_adapter → v5"
        doc["generated_at_utc"] = now
        args.radar_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "applied": True,
                "adapter": V5_ADAPTER,
                "report": _rel(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
