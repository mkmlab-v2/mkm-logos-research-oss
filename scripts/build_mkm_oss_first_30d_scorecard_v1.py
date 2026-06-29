#!/usr/bin/env python3
"""OSS-first 30d scorecard — smoke logs + inbound + community GTM snapshot.

Reproduce:
  py scripts/build_mkm_oss_first_30d_scorecard_v1.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "reports/mkm_oss_first_30d_execution_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
INBOUND = ROOT / "reports/mkm_oss_inbound_inquiry_log_v1.jsonl"
SMOKE = ROOT / "reports/universal_root_oss_cursor_smoke_v1_latest.json"
OUT = ROOT / "reports/mkm_oss_first_30d_scorecard_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _count_inbound() -> tuple[int, int]:
    """Returns (inquiry_count, line_count)."""
    if not INBOUND.is_file():
        return 0, 0
    lines = [ln.strip() for ln in INBOUND.read_text(encoding="utf-8").splitlines() if ln.strip()]
    inquiries = 0
    for ln in lines:
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ch = str(row.get("channel", "")).lower()
        if ch and ch != "none":
            inquiries += 1
    return inquiries, len(lines)


def main() -> int:
    plan = _read_json(PLAN)
    gtm = _read_json(GTM)
    smoke = _read_json(SMOKE)
    inbound_count, log_lines = _count_inbound()

    disc = (gtm.get("channels") or {}).get("github_discussions") or {}
    external_repro = int(disc.get("external_repro_reports") or 0)
    targets = plan.get("success_metrics_30d") or {}

    smoke_ok = smoke.get("ok") is True
    smoke_pass = int((plan.get("scorecard") or {}).get("smoke_pass_count") or 0)
    if smoke_ok:
        smoke_pass = max(smoke_pass, 1)

    met = {
        "external_repro": external_repro >= int(targets.get("external_repro_reports_target") or 2),
        "inbound": inbound_count >= int(targets.get("inbound_inquiry_target") or 1),
        "smoke_weekly": smoke_pass >= int(targets.get("weekly_smoke_pass_target") or 4),
    }
    any_traction = external_repro >= 2 or inbound_count >= 1

    out = {
        "schema": "mkm_oss_first_30d_scorecard_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "plan_ssot": str(PLAN.relative_to(ROOT)).replace("\\", "/"),
        "metrics": {
            "external_repro_reports": external_repro,
            "external_repro_target": targets.get("external_repro_reports_target"),
            "inbound_inquiry_count": inbound_count,
            "inbound_log_lines": log_lines,
            "inbound_target": targets.get("inbound_inquiry_target"),
            "smoke_ok_latest": smoke_ok,
            "smoke_pass_count_recorded": smoke_pass,
            "oss_smoke_artifact": str(SMOKE.relative_to(ROOT)).replace("\\", "/") if smoke else None,
        },
        "targets_met": met,
        "go_no_go_hint": "review_pilot_sow_on_inbound" if inbound_count >= 1 else (
            "continue_oss" if any_traction else "continue_oss_no_traction_yet"
        ),
        "revenue_target_krw": None,
        "reproduce": "py scripts/build_mkm_oss_first_30d_scorecard_v1.py",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if plan:
        plan.setdefault("scorecard", {})
        plan["scorecard"].update({
            "last_updated_utc": out["generated_at_utc"],
            "smoke_pass_count": smoke_pass,
            "external_repro_reports": external_repro,
            "inbound_inquiry_count": inbound_count,
        })
        PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(OUT), "go_no_go_hint": out["go_no_go_hint"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
