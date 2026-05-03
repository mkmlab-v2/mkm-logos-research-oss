#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PoC: gated child-process launcher with Execution Clearance Certificate (ECC).

Reads integrated governance (Fact-Lock artifact). When final_regime is HOLD and
action is TRADE_EXECUTE, refuses to inject API material and exits without spawning
the trade path — **DPAPI is not queried on HOLD** (double lock).

Optional ``--target NAME``: after APPROVED, resolve secret via ``security_agent_manager``
(DPAPI store); ``NAME`` is both the store key and the child ``os.environ`` key.
If missing from store, exit 1. Without ``--target``, TRADE_EXECUTE keeps PoC behaviour
(injects fake ``BINANCE_API_KEY`` only in child env).

Does not replace VPS secrets management; local bypass remains possible without this
entrypoint.

Optional: set ``ATHENA_ECC_AUDIT_WEBHOOK_URL`` to POST a minimal audit summary (no secrets)
after each append-only audit row. Failures are non-fatal. ``--no-audit-webhook`` disables.

Usage:
  py scripts/athena_run_v1.py --target BINANCE_API_KEY -- py scripts/trade_dummy.py

  py scripts/athena_run_v1.py --governance-json scripts/fixtures/integrated_governance_v1_hold.json -- \\
      py scripts/trade_dummy.py

  py scripts/athena_run_v1.py -- py scripts/trade_dummy.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOV = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "integrated_governance_v1_latest.json"
DEFAULT_ECC_OUT = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "ecc_execution_clearance_latest.json"
DEFAULT_INTEGRITY = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "env_integrity_report_v1_latest.json"
DEFAULT_AUDIT_JSONL = WORKSPACE_ROOT / "reports" / "athena_ecc_audit.jsonl"

AUDIT_ROW_SCHEMA = "athena_ecc_audit_row_v1"
WEBHOOK_SCHEMA = "athena_ecc_audit_webhook_v1"


def _build_remote_audit_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Minimal JSON for POST; no secret material (no child env, no DPAPI values)."""
    ecc = row.get("ecc") if isinstance(row.get("ecc"), dict) else None
    body: dict[str, Any] = {
        "schema": WEBHOOK_SCHEMA,
        "schema_version": "1.0.0",
        "recorded_at_utc": row.get("recorded_at_utc"),
        "process_exit_code": row.get("process_exit_code"),
        "ecc_payload_sha256": row.get("ecc_payload_sha256"),
        "ecc_out": row.get("ecc_out"),
    }
    if ecc:
        body["ecc_status"] = ecc.get("status")
        body["ecc_reason"] = ecc.get("reason")
        body["final_regime"] = ecc.get("final_regime")
        body["action_payload_hash"] = ecc.get("action_payload_hash")
        body["governance_artifact"] = ecc.get("governance_artifact")
        body["action"] = ecc.get("action")
    else:
        body["kind"] = row.get("kind")
        body["detail"] = row.get("detail")
        body["target"] = row.get("target")
        ga = row.get("governance_artifact")
        if ga:
            body["governance_artifact"] = ga
    return {k: v for k, v in body.items() if v is not None}


def _maybe_post_audit_webhook(row: dict[str, Any], *, post_webhook: bool) -> None:
    if not post_webhook:
        return
    url = (os.environ.get("ATHENA_ECC_AUDIT_WEBHOOK_URL") or "").strip()
    if not url:
        return
    payload = _build_remote_audit_payload(row)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "athena_run_v1/1.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            resp.read(8192)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"athena_run_v1: audit webhook POST failed (non-fatal): {exc}", file=sys.stderr)

SCHEMA_ECC = "execution_clearance_certificate_v1"
FAKE_BINANCE_KEY = "FAKE_BINANCE_KEY_1234"
DENIED_MSG = "ECC DENIED: Governance is in HOLD mode."

_STORE_MISS = (
    "athena_run_v1: Key not found in Secret Store. "
    "Register it (e.g. scripts/Invoke-EncryptedSecretStore.ps1 -Action set -Key <NAME>) "
    "or see CONSTITUTION §1.1.2 (security_agent_manager)."
)


def _resolve_secret(target: str) -> str | None:
    """Load plaintext for *target* key name from DPAPI-backed store (same as env var name)."""
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    from scripts.security_agent_manager import get_security_agent

    return get_security_agent().get_env_var(target)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ValueError(f"expected JSON object in {path}")
    return doc


def _is_hold(gov: dict[str, Any]) -> bool:
    regime = str(gov.get("final_regime") or "").strip().upper()
    if regime == "HOLD":
        return True
    return not bool(gov.get("final_action_allowed", False))


def _integrity_green(path: Path | None) -> tuple[bool, str]:
    if path is None or not path.exists():
        return True, "no_integrity_report_assumed_green_poc"
    try:
        doc = _load_json(path)
    except Exception as exc:
        return False, f"integrity_read_failed:{exc}"
    status = str(doc.get("status") or doc.get("integrity_status") or "").strip().upper()
    if status == "GREEN":
        return True, "integrity_green"
    return False, f"integrity_not_green:{status or 'EMPTY'}"


def _payload_hash(argv: list[str]) -> str:
    joined = "\x00".join(argv).encode("utf-8", errors="replace")
    return hashlib.sha256(joined).hexdigest()


def _ecc_payload(
    *,
    status: str,
    reason: str,
    gov_path: Path,
    gov: dict[str, Any],
    action: str,
    child_argv: list[str] | None,
    child_exit: int | None,
    audit_note: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_ECC,
        "schema_version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "status": status,
        "reason": reason,
        "governance_artifact": str(gov_path.relative_to(WORKSPACE_ROOT)) if gov_path.is_relative_to(WORKSPACE_ROOT) else str(gov_path),
        "final_regime": gov.get("final_regime"),
        "final_action_allowed": gov.get("final_action_allowed"),
        "action": action,
        "action_payload_hash": _payload_hash(child_argv or []),
        "child_command": child_argv,
        "child_exit_code": child_exit,
        "audit_ref": audit_note,
    }


def _write_ecc(out_path: Path, payload: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ecc_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _append_audit_jsonl(
    audit_path: Path,
    *,
    ecc_out: Path,
    payload: dict[str, Any],
    process_exit_code: int,
    post_webhook: bool = True,
) -> None:
    rel_ecc = str(ecc_out.relative_to(WORKSPACE_ROOT)) if ecc_out.is_relative_to(WORKSPACE_ROOT) else str(ecc_out)
    row = {
        "schema": AUDIT_ROW_SCHEMA,
        "schema_version": "1.0.0",
        "recorded_at_utc": _now_utc(),
        "ecc_out": rel_ecc,
        "process_exit_code": process_exit_code,
        "ecc_payload_sha256": _ecc_sha256(payload),
        "ecc": payload,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _maybe_post_audit_webhook(row, post_webhook=post_webhook)


def _append_audit_abort(
    audit_path: Path,
    *,
    kind: str,
    detail: str,
    gov_path: Path | None,
    target: str | None,
    child_argv: list[str] | None,
    process_exit_code: int,
    post_webhook: bool = True,
) -> None:
    row = {
        "schema": AUDIT_ROW_SCHEMA,
        "schema_version": "1.0.0",
        "recorded_at_utc": _now_utc(),
        "kind": kind,
        "detail": detail,
        "governance_artifact": str(gov_path.relative_to(WORKSPACE_ROOT)) if gov_path and gov_path.is_relative_to(WORKSPACE_ROOT) else (str(gov_path) if gov_path else None),
        "target": target,
        "child_command": child_argv,
        "process_exit_code": process_exit_code,
        "ecc": None,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _maybe_post_audit_webhook(row, post_webhook=post_webhook)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Athena gated run (ECC PoC).")
    ap.add_argument(
        "--governance-json",
        type=Path,
        default=DEFAULT_GOV,
        help="Path to integrated_governance_v1 JSON.",
    )
    ap.add_argument(
        "--ecc-out",
        type=Path,
        default=DEFAULT_ECC_OUT,
        help="Write Execution Clearance Certificate JSON here.",
    )
    ap.add_argument(
        "--action",
        default="TRADE_EXECUTE",
        choices=("TRADE_EXECUTE", "OBSERVE_ONLY"),
        help="Declared action for policy check.",
    )
    ap.add_argument(
        "--integrity-json",
        type=Path,
        default=None,
        help=f"Optional integrity report (defaults to {DEFAULT_INTEGRITY} if present).",
    )
    ap.add_argument(
        "--no-default-integrity-path",
        action="store_true",
        help="Do not fall back to docs/.../env_integrity_report_v1_latest.json.",
    )
    ap.add_argument(
        "--target",
        default=None,
        metavar="KEY_NAME",
        help="DPAPI secret key name = child env var (e.g. BINANCE_API_KEY). Omit for PoC fake key.",
    )
    ap.add_argument(
        "--audit-jsonl",
        type=Path,
        default=DEFAULT_AUDIT_JSONL,
        help="Append-only audit log (JSONL). Default: reports/athena_ecc_audit.jsonl",
    )
    ap.add_argument(
        "--no-audit-append",
        action="store_true",
        help="Do not append to audit JSONL.",
    )
    ap.add_argument(
        "--no-audit-webhook",
        action="store_true",
        help="Do not POST remote audit summary (see ATHENA_ECC_AUDIT_WEBHOOK_URL).",
    )
    ap.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command after -- : e.g. -- py scripts/trade_dummy.py",
    )
    args = ap.parse_args(argv)

    cmd = list(args.cmd or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("athena_run_v1: missing command; use: py scripts/athena_run_v1.py -- <command...>", file=sys.stderr)
        return 1

    gov_path = args.governance_json
    if not gov_path.is_file():
        print(f"athena_run_v1: governance file not found: {gov_path}", file=sys.stderr)
        return 1

    gov = _load_json(gov_path)
    if str(gov.get("schema") or "") != "integrated_governance_v1":
        print("athena_run_v1: governance schema must be integrated_governance_v1", file=sys.stderr)
        return 1

    print(f"athena doctor (preflight): governance OK — regime={gov.get('final_regime')}", file=sys.stderr)

    hold = _is_hold(gov)
    integ_path = args.integrity_json
    if integ_path is None and not args.no_default_integrity_path:
        integ_path = DEFAULT_INTEGRITY if DEFAULT_INTEGRITY.exists() else None
    elif args.no_default_integrity_path and args.integrity_json is None:
        integ_path = None

    ok_i, reason_i = _integrity_green(integ_path)

    def _emit_ecc(payload: dict[str, Any], proc_exit: int) -> None:
        _write_ecc(args.ecc_out, payload)
        if not args.no_audit_append:
            _append_audit_jsonl(
                args.audit_jsonl,
                ecc_out=args.ecc_out,
                payload=payload,
                process_exit_code=proc_exit,
                post_webhook=not args.no_audit_webhook,
            )

    # HOLD + trade-like action => DENIED
    if args.action == "TRADE_EXECUTE" and hold:
        audit = f"ecc_denied_hold:{gov_path.name}"
        pl = _ecc_payload(
            status="DENIED",
            reason="governance_hold_trade_execute",
            gov_path=gov_path,
            gov=gov,
            action=args.action,
            child_argv=cmd,
            child_exit=None,
            audit_note=audit,
        )
        _emit_ecc(pl, 2)
        print(DENIED_MSG, file=sys.stderr)
        return 2

    if args.action == "TRADE_EXECUTE" and not ok_i:
        audit = f"ecc_denied_integrity:{reason_i}"
        pl = _ecc_payload(
            status="DENIED",
            reason=reason_i,
            gov_path=gov_path,
            gov=gov,
            action=args.action,
            child_argv=cmd,
            child_exit=None,
            audit_note=audit,
        )
        _emit_ecc(pl, 2)
        print(f"ECC DENIED: {reason_i}", file=sys.stderr)
        return 2

    if args.action == "OBSERVE_ONLY":
        env = os.environ.copy()
        audit = "ecc_approved_observe_no_secret_injection"
        proc = subprocess.run(cmd, env=env, cwd=str(WORKSPACE_ROOT))
        pl = _ecc_payload(
            status="APPROVED",
            reason="observe_only",
            gov_path=gov_path,
            gov=gov,
            action=args.action,
            child_argv=cmd,
            child_exit=int(proc.returncode),
            audit_note=audit,
        )
        _emit_ecc(pl, int(proc.returncode))
        return int(proc.returncode)

    # TRADE_EXECUTE + ATTACK + integrity OK => inject secrets only in child env (never write .env)
    env = os.environ.copy()
    if args.target:
        secret = _resolve_secret(args.target.strip())
        if not secret:
            print(_STORE_MISS, file=sys.stderr)
            if os.name != "nt":
                print(
                    "athena_run_v1: DPAPI secret store requires Windows (NT).",
                    file=sys.stderr,
                )
            if not args.no_audit_append:
                _append_audit_abort(
                    args.audit_jsonl,
                    kind="ABORTED_SECRET_STORE_MISS",
                    detail=args.target.strip(),
                    gov_path=gov_path,
                    target=args.target.strip(),
                    child_argv=cmd,
                    process_exit_code=1,
                    post_webhook=not args.no_audit_webhook,
                )
            return 1
        env[args.target.strip()] = secret
        audit = f"ecc_approved_dpapi_in_flight:{args.target.strip()}"
    else:
        env["BINANCE_API_KEY"] = FAKE_BINANCE_KEY
        audit = "ecc_approved_trade_dummy_key_in_child_only"
    proc = subprocess.run(cmd, env=env, cwd=str(WORKSPACE_ROOT))
    pl = _ecc_payload(
        status="APPROVED",
        reason="governance_attack_integrity_ok",
        gov_path=gov_path,
        gov=gov,
        action=args.action,
        child_argv=cmd,
        child_exit=int(proc.returncode),
        audit_note=audit,
    )
    _emit_ecc(pl, int(proc.returncode))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
