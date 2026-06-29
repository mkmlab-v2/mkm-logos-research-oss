#!/usr/bin/env python3
"""WTT operator panel n≥30 gate — internal dogfood, NOT customer/SEND eligible [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TENANT = "wtt-operator-panel-v1"
DEFAULT_INTAKE = ROOT / "data/wtt/intake/wtt-operator-panel-v1.jsonl"
DEFAULT_PROVENANCE = ROOT / "data/wtt/provenance/wtt-operator-panel-v1.provenance.json"
DEFAULT_OUT = ROOT / "reports/wtt_operator_panel_gate_v1_latest.json"
CHECK_PROVENANCE = ROOT / "scripts/check_wtt_pilot_provenance_v1.py"
TARGET_N = 30

OPERATOR_LABELS_REQUIRED = frozenset({"operator_panel", "internal_dogfood"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_lines(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _count_operator_sessions(path: Path) -> tuple[int, list[str]]:
    ids: list[str] = []
    for row in _load_lines(path):
        labels = set(row.get("labels") or [])
        if not OPERATOR_LABELS_REQUIRED.issubset(labels):
            continue
        if row.get("customer_provided") is True:
            continue
        ids.append(str(row.get("session_id", "")))
    return len(ids), ids


def evaluate(
    *,
    tenant_id: str,
    intake_path: Path,
    provenance_path: Path,
    target_n: int,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    session_n, sample_ids = _count_operator_sessions(intake_path)

    if not intake_path.is_file():
        issues.append({"code": "missing_intake", "message": str(intake_path)})
    elif session_n < target_n:
        issues.append(
            {
                "code": "session_count",
                "message": f"operator_panel sessions {session_n} < {target_n}",
            }
        )

    for row in _load_lines(intake_path):
        labels = set(row.get("labels") or [])
        if "operator_panel" in labels and row.get("customer_provided") is True:
            issues.append(
                {
                    "code": "customer_provided_conflict",
                    "message": f"operator_panel row must have customer_provided=false: {row.get('session_id')}",
                }
            )

    prov_ok = False
    prov_report: dict[str, Any] = {}
    if provenance_path.is_file():
        proc = subprocess.run(
            [
                sys.executable,
                str(CHECK_PROVENANCE),
                "--tenant-id",
                tenant_id,
                "--provenance",
                str(provenance_path),
                "--intake-jsonl",
                str(intake_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            prov_report = json.loads((proc.stdout or "").strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            prov_report = {"ok": proc.returncode == 0}
        prov_ok = proc.returncode == 0
        if not prov_ok:
            issues.append({"code": "provenance_gate", "message": "check_wtt_pilot_provenance failed"})
    else:
        issues.append({"code": "missing_provenance", "message": str(provenance_path)})

    gate_met = session_n >= target_n and prov_ok and len(issues) == 0

    return {
        "schema": "wtt_operator_panel_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "tenant_id": tenant_id,
        "panel_lane": "operator_panel",
        "target_n_sessions": target_n,
        "operator_panel_sessions_collected": session_n,
        "operator_panel_n30_gate_met": gate_met,
        "not_eligible_for_send": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "intake_jsonl": str(intake_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        if intake_path.is_file()
        else None,
        "provenance_path": str(provenance_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        if provenance_path.is_file()
        else None,
        "provenance_gate_ok": prov_ok,
        "session_ids_sample": sample_ids[:5],
        "issue_count": len(issues),
        "issues": issues,
        "note_ko": (
            f"운영자 패널 {session_n}/{target_n}. gate_met={gate_met}. "
            "실고객·SEND·Track A 증거로 승격 불가(not_eligible_for_send)."
        ),
        "one_click": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts/Invoke-WttOperatorPanelRoutine_v1.ps1"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default=DEFAULT_TENANT)
    ap.add_argument("--intake-jsonl", type=Path, default=DEFAULT_INTAKE)
    ap.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    ap.add_argument("--target-n", type=int, default=TARGET_N)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    report = evaluate(
        tenant_id=args.tenant_id,
        intake_path=args.intake_jsonl.resolve(),
        provenance_path=args.provenance.resolve(),
        target_n=args.target_n,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["operator_panel_n30_gate_met"],
                "collected": report["operator_panel_sessions_collected"],
                "target_n": report["target_n_sessions"],
                "gate_met": report["operator_panel_n30_gate_met"],
            }
        )
    )
    if args.strict and not report["operator_panel_n30_gate_met"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
