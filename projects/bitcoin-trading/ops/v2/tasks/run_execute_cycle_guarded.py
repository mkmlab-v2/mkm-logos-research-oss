from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNNER = PROJECT_ROOT / "ops" / "v2" / "graph" / "runner.py"
STATE_PATH = PROJECT_ROOT / "memory" / "v2" / "latest_state.json"
RISK_POLICY_PATH = PROJECT_ROOT / "ops" / "v2" / "policies" / "risk_policy.yaml"
APPROVAL_PATH = PROJECT_ROOT / "memory" / "v2" / "ops" / "execute_approval.json"
APPROVAL_USED_PATH = PROJECT_ROOT / "memory" / "v2" / "ops" / "execute_approval_used_jti.jsonl"
GUARD_LOG = PROJECT_ROOT / "memory" / "v2" / "ops" / "execute_guard.log"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _append_guard_log(message: str) -> None:
    GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with GUARD_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")


def _run_runner(*args: str) -> int:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=str(PROJECT_ROOT),
    )
    return proc.returncode


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_require_human_approval() -> bool:
    if not RISK_POLICY_PATH.exists():
        return False
    try:
        loaded = yaml.safe_load(RISK_POLICY_PATH.read_text(encoding="utf-8")) or {}
        risk_policy = loaded.get("risk_policy") if isinstance(loaded, dict) else {}
        if isinstance(risk_policy, dict):
            return bool(risk_policy.get("require_human_approval_for_execute", False))
        return False
    except Exception:
        # Fail-safe
        return True


def _is_jti_used(jti: str) -> bool:
    if not APPROVAL_USED_PATH.exists():
        return False
    with APPROVAL_USED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if jti and jti in line:
                return True
    return False


def _verify_approval_signature(approval: dict[str, Any], key: str) -> bool:
    to_sign = "|".join(
        [
            str(approval.get("approved")),
            str(approval.get("approved_at_utc")),
            str(approval.get("approved_until_utc")),
            str(approval.get("approved_by")),
            str(approval.get("reason")),
            str(approval.get("ttl_minutes")),
            str(approval.get("single_use")),
            str(approval.get("jti")),
        ]
    )
    calc = hmac.new(key.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest().lower()
    sig = str(approval.get("signature", "")).strip().lower()
    return hmac.compare_digest(calc, sig)


def _consume_approval(approval: dict[str, Any]) -> None:
    approval_used_dir = APPROVAL_USED_PATH.parent
    approval_used_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "ts_utc": _utc_now(),
        "jti": approval.get("jti"),
        "single_use": bool(approval.get("single_use", True)),
        "approved_by": approval.get("approved_by"),
        "approved_until_utc": approval.get("approved_until_utc"),
        "result": "consumed",
    }
    with APPROVAL_USED_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    if bool(approval.get("single_use", True)) and APPROVAL_PATH.exists():
        APPROVAL_PATH.unlink(missing_ok=True)
        _append_guard_log(f"APPROVAL_CONSUMED jti={approval.get('jti')}")
    else:
        _append_guard_log(f"APPROVAL_REUSED_ALLOWED jti={approval.get('jti')}")


def main() -> int:
    if not RUNNER.exists():
        print(f"runner.py not found: {RUNNER}", file=sys.stderr)
        return 2

    rc = _run_runner("--mode", "read-only")
    if rc != 0:
        print(f"preflight read-only cycle failed with exit code: {rc}", file=sys.stderr)
        return rc

    if not STATE_PATH.exists():
        print(f"latest_state.json not found: {STATE_PATH}", file=sys.stderr)
        return 3

    state = _load_json(STATE_PATH)
    rg = state.get("risk_mode_guardrail") if isinstance(state.get("risk_mode_guardrail"), dict) else {}
    block_execute = bool(rg.get("block_execute", False))
    proposed_mode = str(rg.get("proposed_mode", "read-only"))
    risk_score = int(rg.get("risk_score", 0))

    require_human_approval = _load_require_human_approval()
    approval: dict[str, Any] | None = None

    if require_human_approval:
        hmac_key = os.getenv("EXECUTE_APPROVAL_HMAC_KEY", "").strip()
        if not hmac_key:
            _append_guard_log("EXECUTE_SKIPPED reason=approval_hmac_key_missing")
            print("Execute skipped by policy gate: EXECUTE_APPROVAL_HMAC_KEY missing")
            return 0
        if not APPROVAL_PATH.exists():
            _append_guard_log("EXECUTE_SKIPPED reason=require_human_approval_missing")
            print("Execute skipped by policy gate: approval file missing")
            return 0

        try:
            approval = _load_json(APPROVAL_PATH)
        except Exception:
            _append_guard_log("EXECUTE_SKIPPED reason=approval_parse_error")
            print("Execute skipped by policy gate: approval parse error")
            return 0

        jti = str(approval.get("jti", "")).strip()
        if not jti:
            _append_guard_log("EXECUTE_SKIPPED reason=approval_jti_missing")
            print("Execute skipped by policy gate: approval jti missing")
            return 0

        single_use = bool(approval.get("single_use", True))
        if single_use and _is_jti_used(jti):
            _append_guard_log(f"EXECUTE_SKIPPED reason=approval_replay_detected jti={jti}")
            print(f"Execute skipped by policy gate: approval replay detected (jti={jti})")
            return 0

        approved_until = str(approval.get("approved_until_utc", "")).strip()
        try:
            approved_until_dt = datetime.fromisoformat(approved_until.replace("Z", "+00:00")).astimezone(UTC)
            if datetime.now(UTC) > approved_until_dt:
                _append_guard_log(f"EXECUTE_SKIPPED reason=approval_expired approved_until={approved_until}")
                print(f"Execute skipped by policy gate: approval expired at {approved_until}")
                return 0
        except Exception:
            _append_guard_log("EXECUTE_SKIPPED reason=approval_parse_error")
            print("Execute skipped by policy gate: approval parse error")
            return 0

        if not _verify_approval_signature(approval, hmac_key):
            _append_guard_log("EXECUTE_SKIPPED reason=approval_signature_invalid")
            print("Execute skipped by policy gate: approval signature invalid")
            return 0

    if block_execute or proposed_mode == "shadow":
        reason = "block_execute=true" if block_execute else "proposed_mode=shadow"
        _append_guard_log(f"EXECUTE_SKIPPED reason={reason} risk_score={risk_score}")
        print(f"Execute skipped by guardrail: {reason} (risk_score={risk_score})")
        return 0

    execute_args = ["--mode", "execute"]
    if require_human_approval:
        execute_args.append("--execute-approved")
    rc = _run_runner(*execute_args)
    if rc != 0:
        print(f"v2 guarded execute cycle failed with exit code: {rc}", file=sys.stderr)
        return rc

    _append_guard_log(f"EXECUTE_RAN risk_score={risk_score}")
    print(f"Execute ran (risk_score={risk_score})")

    if require_human_approval and approval is not None:
        _consume_approval(approval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
