#!/usr/bin/env python3
"""Build single-file trading GO/NO_GO readiness status (disk SSOT only).

This script does not place orders and does not call network endpoints.
It consolidates local artifacts into one deterministic verdict JSON.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "reports" / "poc_binance_signal_webhook" / "conditional_gate_latest.json"
DEFAULT_APPROVAL = ROOT / "reports" / "trading_human_execution_approval_latest.json"
DEFAULT_RISK = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "trading_go_no_go_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    txt = raw.strip()
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_json_obj(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _check_gate(path: Path, out: dict[str, Any], reasons: list[str]) -> bool:
    doc = _read_json_obj(path)
    out["gate_summary_path"] = str(path)
    if doc is None:
        reasons.append("missing_or_invalid_gate_summary")
        out["gate_ok"] = False
        return False
    ok = bool(doc.get("gate_ok") is True)
    out["gate_ok"] = ok
    out["gate_reason"] = doc.get("gate_reason")
    out["backend"] = doc.get("backend")
    if not ok:
        reasons.append("gate_not_ok")
    return ok


def _check_approval(path: Path, out: dict[str, Any], reasons: list[str]) -> bool:
    doc = _read_json_obj(path)
    out["approval_path"] = str(path)
    if doc is None:
        reasons.append("missing_or_invalid_human_approval")
        out["approval_ok"] = False
        return False

    ok = True
    if doc.get("schema") != "trading_human_execution_approval_v1":
        ok = False
        reasons.append("approval_schema_mismatch")
    if doc.get("decision") != "GO":
        ok = False
        reasons.append("approval_decision_not_go")
    vdt = _parse_iso_utc(str(doc.get("valid_until_utc") or ""))
    if vdt is None:
        ok = False
        reasons.append("approval_valid_until_invalid")
    elif datetime.now(timezone.utc) > vdt:
        ok = False
        reasons.append("approval_expired")

    out["approval_ok"] = ok
    out["approval_decision"] = doc.get("decision")
    out["approval_valid_until_utc"] = doc.get("valid_until_utc")
    out["approval_proposal_id"] = doc.get("proposal_id")
    out["approval_nonce"] = doc.get("nonce")
    return ok


def _check_risk(path: Path, out: dict[str, Any], reasons: list[str]) -> bool:
    doc = _read_json_obj(path)
    out["risk_profile_path"] = str(path)
    if doc is None:
        reasons.append("missing_or_invalid_risk_profile")
        out["risk_ok"] = False
        return False

    ok = True
    exp = _parse_iso_utc(str(doc.get("expires_at") or ""))
    if exp is None:
        ok = False
        reasons.append("risk_expires_at_invalid")
    elif datetime.now(timezone.utc) > exp:
        ok = False
        reasons.append("risk_profile_expired")

    tg = doc.get("trinity_governor")
    mode = ""
    if isinstance(tg, dict):
        mode = str(tg.get("mode") or "").upper()
        if mode == "LOCKED_MODE":
            ok = False
            reasons.append("risk_locked_mode")
    gb = doc.get("governance_bridge")
    final_allowed = None
    if isinstance(gb, dict):
        final_allowed = gb.get("final_action_allowed")
        if final_allowed is False:
            ok = False
            reasons.append("risk_governance_denied")

    out["risk_ok"] = ok
    out["risk_mode"] = mode or None
    out["risk_expires_at"] = doc.get("expires_at")
    out["risk_final_action_allowed"] = final_allowed
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-summary", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--approval-json", type=Path, default=DEFAULT_APPROVAL)
    ap.add_argument("--risk-json", type=Path, default=DEFAULT_RISK)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate_path = args.gate_summary if args.gate_summary.is_absolute() else (ROOT / args.gate_summary)
    approval_path = args.approval_json if args.approval_json.is_absolute() else (ROOT / args.approval_json)
    risk_path = args.risk_json if args.risk_json.is_absolute() else (ROOT / args.risk_json)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    reasons: list[str] = []
    checks: dict[str, Any] = {
        "schema": "trading_go_no_go_status_v1",
        "generated_at_utc": _utc_now(),
    }
    gate_ok = _check_gate(gate_path, checks, reasons)
    approval_ok = _check_approval(approval_path, checks, reasons)
    risk_ok = _check_risk(risk_path, checks, reasons)
    overall = bool(gate_ok and approval_ok and risk_ok)

    checks["go_no_go"] = "GO" if overall else "NO_GO"
    checks["reasons"] = reasons
    checks["notes"] = (
        "Disk SSOT readiness only; this file itself does not place orders. "
        "Live execution still requires explicit operator command path."
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"GO_NO_GO={checks['go_no_go']}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

