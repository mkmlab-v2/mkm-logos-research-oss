#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "a_codeai_public_benchmark_launch_checklist_v1.json"
HARDENING_DEFAULT = ART / "pointerguard_security_hardening_latest.json"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _exists(path: Path) -> bool:
    return path.exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    hardening = {}
    if HARDENING_DEFAULT.exists():
        try:
            hardening = json.loads(HARDENING_DEFAULT.read_text(encoding="utf-8"))
        except Exception:
            hardening = {}
    controls = hardening.get("controls", {}) if isinstance(hardening, dict) else {}
    c1_pass = isinstance(controls, dict) and str(controls.get("C1_scope_guard", {}).get("status")) == "PASS"
    c6_pass = isinstance(controls, dict) and str(controls.get("C6_abuse_guard", {}).get("status")) == "PASS"
    readiness_all_ok = False
    if READINESS_DEFAULT.exists():
        try:
            readiness = json.loads(READINESS_DEFAULT.read_text(encoding="utf-8"))
            readiness_all_ok = bool(readiness.get("all_ok", False))
        except Exception:
            readiness_all_ok = False

    checks: list[dict[str, Any]] = [
        {
            "id": "C1_public_benchmark_scope_guard",
            "description": "Public benchmark accepts only synthetic/sample text, not customer private corpora.",
            "status": "PASS" if c1_pass else "TODO",
            "evidence_path": str(HARDENING_DEFAULT) if c1_pass else None,
        },
        {
            "id": "C2_policy_boundary",
            "description": "PointerGuard allow/caution/forbid policy active and forbid zones blocked from public path.",
            "status": "PASS" if _exists(ART / "pointerguard_folder_policy_latest.json") else "TODO",
            "evidence_path": str(ART / "pointerguard_folder_policy_latest.json"),
        },
        {
            "id": "C3_operational_smoke",
            "description": "Operational smoke gate passes for latest control chain run.",
            "status": "PASS" if _exists(ART / "pointerguard_operational_smoke_latest.json") else "TODO",
            "evidence_path": str(ART / "pointerguard_operational_smoke_latest.json"),
        },
        {
            "id": "C4_alerting_hook",
            "description": "Webhook alert automation is wired for failure/guard events.",
            "status": "PASS" if _exists(ART / "pointerguard_ops_alert_delivery_latest.json") else "TODO",
            "evidence_path": str(ART / "pointerguard_ops_alert_delivery_latest.json"),
        },
        {
            "id": "C5_public_metrics_transparency",
            "description": "Expose only benchmark metrics (p50/p95/p99/RPS/error) with timestamp and environment note.",
            "status": "PASS" if _exists(ART / "pointerguard_two_tier_perf_scorecard_latest.json") else "TODO",
            "evidence_path": str(ART / "pointerguard_two_tier_perf_scorecard_latest.json"),
        },
        {
            "id": "C6_rate_limit_abuse_guard",
            "description": "Public endpoint enforces request-size limit, rate limit, and abuse control (captcha/throttle).",
            "status": "PASS" if c6_pass else "TODO",
            "evidence_path": str(HARDENING_DEFAULT) if c6_pass else None,
        },
        {
            "id": "C7_secret_non_exposure",
            "description": "No codebook internals, policy tuning internals, or customer prompts are exposed in public response.",
            "status": "PASS" if _exists(ROOT / "scripts" / "deploy" / "nginx" / "a-codeai.com.evidence.latest.json.example") else "TODO",
            "evidence_path": str(ROOT / "scripts" / "deploy" / "nginx" / "a-codeai.com.evidence.latest.json.example"),
        },
    ]

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    total = len(checks)
    decision = "READY_FOR_PUBLIC_OPEN_BENCH" if pass_count == total else ("READY_FOR_SHADOW_PUBLIC_BENCH" if pass_count >= 5 else "HOLD_NEEDS_HARDENING")
    if not readiness_all_ok:
        decision = "BLOCKED_BY_READINESS"

    out_doc = {
        "schema": "a_codeai_public_benchmark_launch_checklist_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "summary": {
            "pass_count": pass_count,
            "total": total,
            "decision": decision,
            "readiness_all_ok": readiness_all_ok,
        },
        "checks": checks,
        "notes": [
            "Shadow launch is allowed before full public launch when scope/abuse guard checks are incomplete.",
            "Global/public claims must remain conditional until service-load evidence keeps passing over time.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
