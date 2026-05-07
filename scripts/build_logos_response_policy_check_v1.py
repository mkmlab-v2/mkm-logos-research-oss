#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_WEEKLY_GATE = ART / "logos_shadow_weekly_gate_latest.json"
DEFAULT_WEEKLY_TREND = ART / "logos_shadow_weekly_trend_report_latest.json"
DEFAULT_ALERT = ART / "logos_shadow_alert_decision_latest.json"
DEFAULT_INSIGHT = ART / "logos_shadow_insight_latest.json"
DEFAULT_POLICY_DOC = ART / "LOGOS_RESPONSE_POLICY_INTERNAL_EXTERNAL_V1.md"
DEFAULT_OUT = ART / "logos_response_policy_check_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _exists_nonempty(path: Path) -> bool:
    return path.is_file() and bool(path.read_text(encoding="utf-8-sig").strip())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Logos response policy check status.")
    ap.add_argument("--weekly-gate-json", type=Path, default=DEFAULT_WEEKLY_GATE)
    ap.add_argument("--weekly-trend-json", type=Path, default=DEFAULT_WEEKLY_TREND)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--policy-doc-md", type=Path, default=DEFAULT_POLICY_DOC)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    weekly_gate_path = args.weekly_gate_json if args.weekly_gate_json.is_absolute() else ROOT / args.weekly_gate_json
    weekly_trend_path = args.weekly_trend_json if args.weekly_trend_json.is_absolute() else ROOT / args.weekly_trend_json
    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    insight_path = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
    policy_doc_path = args.policy_doc_md if args.policy_doc_md.is_absolute() else ROOT / args.policy_doc_md
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    checks = {
        "policy_doc_exists": _exists_nonempty(policy_doc_path),
        "weekly_gate_exists": weekly_gate_path.is_file(),
        "weekly_trend_exists": weekly_trend_path.is_file(),
        "alert_exists": alert_path.is_file(),
        "insight_exists": insight_path.is_file(),
    }

    if checks["weekly_gate_exists"]:
        gate = _read_json(weekly_gate_path)
        checks["weekly_gate_has_decision"] = isinstance(gate.get("decision"), str) and bool(gate.get("decision"))
    else:
        checks["weekly_gate_has_decision"] = False

    if checks["weekly_trend_exists"]:
        trend = _read_json(weekly_trend_path)
        checks["weekly_trend_has_samples"] = isinstance(trend.get("samples"), int) and trend.get("samples", 0) >= 1
    else:
        checks["weekly_trend_has_samples"] = False

    if checks["alert_exists"]:
        alert = _read_json(alert_path)
        checks["alert_has_should_alert"] = isinstance((alert.get("alert") or {}).get("should_alert"), bool)
    else:
        checks["alert_has_should_alert"] = False

    if checks["insight_exists"]:
        insight = _read_json(insight_path)
        summary = insight.get("summary") or {}
        checks["insight_has_decision"] = isinstance(summary.get("decision"), str) and bool(summary.get("decision"))
        checks["insight_has_deep_fusion_lines"] = bool(summary.get("deep_fusion_evidence_line_1")) and bool(
            summary.get("deep_fusion_evidence_line_2")
        )
    else:
        checks["insight_has_decision"] = False
        checks["insight_has_deep_fusion_lines"] = False

    passed = all(bool(v) for v in checks.values())
    out = {
        "schema": "logos_response_policy_check_v1",
        "generated_at_utc": _now(),
        "status": "OK" if passed else "FAIL",
        "passed": passed,
        "checks": checks,
        "evidence_paths": {
            "policy_doc": str(policy_doc_path.resolve()),
            "weekly_gate_json": str(weekly_gate_path.resolve()),
            "weekly_trend_json": str(weekly_trend_path.resolve()),
            "alert_json": str(alert_path.resolve()),
            "insight_json": str(insight_path.resolve()),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

