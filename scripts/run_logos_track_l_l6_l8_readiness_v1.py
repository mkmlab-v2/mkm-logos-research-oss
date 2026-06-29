#!/usr/bin/env python3
"""Track L L6–L8 readiness: S1 shadow review packet + weekly gate + human approval path."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L45_SCRIPT = ROOT / "scripts/run_logos_track_l_l4_l5_readiness_v1.py"
PACKET_BUILDER = ROOT / "scripts/build_logos_s1_shadow_promotion_review_packet_v1.py"
KPI_BUILDER = ROOT / "scripts/build_logos_shadow_promotion_kpi_progress_v1.py"
APPROVAL_RECORDER = ROOT / "scripts/record_logos_s1_shadow_promotion_human_approval_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json"

WEEKLY_GATE = ROOT / "docs/final/artifacts/logos_shadow_weekly_gate_latest.json"
WEEKLY_BOOT = ROOT / "docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json"
WEEKLY_TREND = ROOT / "docs/final/artifacts/logos_shadow_weekly_trend_report_latest.json"
ALERT = ROOT / "docs/final/artifacts/logos_shadow_alert_decision_latest.json"
KPI = ROOT / "docs/final/artifacts/logos_shadow_promotion_kpi_progress_latest.json"
RESPONSE_POLICY = ROOT / "docs/final/artifacts/logos_response_policy_check_latest.json"
REVIEW_PACKET = ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json"
HUMAN_APPROVAL = ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json"
OP_RULE = ROOT / "docs/final/artifacts/LOGOS_SHADOW_WEEKLY_GATE_OPERATION_RULE_V1.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _run_py(args: list[str], *, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode, tail[-1200:] if len(tail) > 1200 else tail


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def build_report(*, skip_l45: bool, refresh_kpi: bool, rebuild_packet: bool) -> dict[str, Any]:
    l45: dict[str, Any]
    if skip_l45:
        l45_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json")
        l45 = {"skipped": True, "l4_l5_ok": bool(l45_doc.get("l4_l5_ok"))}
    else:
        rc, tail = _run_py([str(L45_SCRIPT), "--skip-l3"], timeout=420)
        l45_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json")
        l45 = {"exit_code": rc, "l4_l5_ok": bool(l45_doc.get("l4_l5_ok")) and rc == 0, "tail": tail}

    kpi_build = {"skipped": True, "ok": True}
    if refresh_kpi and KPI_BUILDER.is_file():
        rc, tail = _run_py([str(KPI_BUILDER)], timeout=120)
        kpi_build = {"exit_code": rc, "ok": rc == 0, "tail": tail}

    packet_build = {"skipped": True, "ok": REVIEW_PACKET.is_file()}
    if rebuild_packet and PACKET_BUILDER.is_file():
        rc, tail = _run_py([str(PACKET_BUILDER)], timeout=120)
        packet_build = {"exit_code": rc, "ok": rc == 0, "tail": tail}

    gate_doc = _read_json(WEEKLY_GATE)
    boot_doc = _read_json(WEEKLY_BOOT)
    trend_doc = _read_json(WEEKLY_TREND)
    alert_doc = _read_json(ALERT)
    kpi_doc = _read_json(KPI)
    policy_doc = _read_json(RESPONSE_POLICY)
    packet_doc = _read_json(REVIEW_PACKET)
    approval_doc = _read_json(HUMAN_APPROVAL)

    track_l = packet_doc.get("track_l_advisory") if isinstance(packet_doc.get("track_l_advisory"), dict) else {}

    shadow_checks = {
        "weekly_gate": {
            "exists": WEEKLY_GATE.is_file(),
            "decision": gate_doc.get("decision"),
            "samples": gate_doc.get("samples"),
        },
        "bootstrap_gate": {
            "exists": WEEKLY_BOOT.is_file(),
            "decision": boot_doc.get("decision"),
        },
        "weekly_trend": {"exists": WEEKLY_TREND.is_file(), "samples": trend_doc.get("samples")},
        "alert": {
            "exists": ALERT.is_file(),
            "should_alert": alert_doc.get("should_alert"),
        },
        "operation_rule_md": {"exists": OP_RULE.is_file(), "path": _rel(OP_RULE)},
    }
    shadow_ok = bool(
        shadow_checks["weekly_gate"]["exists"]
        and shadow_checks["bootstrap_gate"]["exists"]
        and shadow_checks["weekly_trend"]["exists"]
        and shadow_checks["alert"]["exists"]
        and str(shadow_checks["weekly_gate"].get("decision") or "").upper() in {"GO", "WATCH"}
    )

    kpi_check = {
        "exists": KPI.is_file(),
        "status": kpi_doc.get("status"),
        "passed": kpi_doc.get("passed"),
        "consecutive_strict_go_windows": kpi_doc.get("consecutive_strict_go_windows"),
    }
    kpi_ok = bool(kpi_check["passed"] and kpi_check["status"] == "READY_FOR_REVIEW")

    packet_check = {
        "schema_ok": packet_doc.get("schema") == "logos_s1_shadow_promotion_review_packet_v1",
        "track_l_label": track_l.get("label"),
        "track_l_non_gating": track_l.get("non_gating") is True,
        "shadow_only": (packet_doc.get("track_wall") or {}).get("shadow_only") is True,
        "promotion_to_a_track_allowed": (packet_doc.get("track_wall") or {}).get("promotion_to_a_track_allowed"),
    }
    packet_ok = bool(
        packet_check["schema_ok"]
        and packet_check["track_l_label"] == "Track L"
        and packet_check["track_l_non_gating"]
        and packet_check["shadow_only"]
        and packet_check["promotion_to_a_track_allowed"] is False
    )

    policy_check = {
        "exists": RESPONSE_POLICY.is_file(),
        "passed": policy_doc.get("passed"),
        "status": policy_doc.get("status"),
    }

    approval_check = {
        "exists": HUMAN_APPROVAL.is_file(),
        "schema_ok": approval_doc.get("schema") == "logos_s1_shadow_promotion_human_approval_v1",
        "decision": approval_doc.get("decision"),
        "shadow_only": (approval_doc.get("track_wall") or {}).get("shadow_only") is True,
    }
    approval_ok = bool(approval_check["exists"] and approval_check["schema_ok"] and approval_check["shadow_only"])

    rc_pytest, tail_pytest = _run_py(
        [
            "-m",
            "pytest",
            "tests/test_build_logos_s1_shadow_promotion_review_packet_v1.py",
            "tests/test_record_logos_s1_shadow_promotion_human_approval_v1.py",
            "-q",
            "--tb=short",
        ],
        timeout=180,
    )
    pytest_check = {"exit_code": rc_pytest, "ok": rc_pytest == 0, "tail": tail_pytest}

    l6_l8_ok = bool(
        (l45.get("skipped") or l45.get("l4_l5_ok"))
        and (kpi_build.get("skipped") or kpi_build.get("ok"))
        and (packet_build.get("skipped") or packet_build.get("ok"))
        and shadow_ok
        and kpi_ok
        and packet_ok
        and approval_ok
        and pytest_check["ok"]
    )

    return {
        "schema": "logos_track_l_l6_l8_readiness_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": {
            "logos_non_gating": True,
            "shadow_advisory_only": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
        },
        "l6_l8_ok": l6_l8_ok,
        "checks": {
            "l4_l5_prerequisite": l45,
            "kpi_refresh": kpi_build,
            "review_packet_build": packet_build,
            "shadow_weekly_path": shadow_checks,
            "kpi_contract": kpi_check,
            "review_packet": packet_check,
            "response_policy": policy_check,
            "human_approval": approval_check,
            "s1_shadow_pytest": pytest_check,
        },
        "artifacts": {
            "review_packet": _rel(REVIEW_PACKET),
            "human_approval": _rel(HUMAN_APPROVAL),
            "kpi_progress": _rel(KPI),
        },
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L6–L8",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L6–L8 S1 shadow advisory readiness")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-l45", action="store_true")
    ap.add_argument("--refresh-kpi", action="store_true", help="Run build_logos_shadow_promotion_kpi_progress_v1.py first")
    ap.add_argument("--rebuild-packet", action="store_true", help="Run build_logos_s1_shadow_promotion_review_packet_v1.py first")
    args = ap.parse_args(argv)

    doc = build_report(
        skip_l45=args.skip_l45,
        refresh_kpi=args.refresh_kpi,
        rebuild_packet=args.rebuild_packet,
    )
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["l6_l8_ok"], "wrote": str(out)}, ensure_ascii=False))
    return 0 if doc["l6_l8_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
