from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ALLOWED_GOVERNANCE = {"GREEN", "APPROVED", "GO"}
DEFAULT_ALLOWED_SECURITY = {"GREEN", "PASS"}
DEFAULT_BLOCKED_OPS_MODES = {"HALT", "SAFE"}


@dataclass
class GateInput:
    governance_status: str
    security_status: str
    ops_mode: str
    risk_profile: dict[str, Any]
    intent: dict[str, Any]


def _read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_upper(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text.upper() if text else fallback


def _normalize_governance_status(governance: dict[str, Any]) -> str:
    status_raw = governance.get("status")
    if status_raw is not None and str(status_raw).strip():
        return _normalize_upper(status_raw, "UNKNOWN")
    final_allowed = governance.get("final_action_allowed")
    if isinstance(final_allowed, bool):
        return "GO" if final_allowed else "RED"
    return _normalize_upper(final_allowed, "UNKNOWN")


def _load_gate_input(
    governance_path: Path,
    security_status_path: Path,
    ops_status_path: Path,
    risk_profile_path: Path,
    intent_path: Path,
) -> GateInput:
    governance = _read_json(governance_path)
    security = _read_json(security_status_path)
    ops = _read_json(ops_status_path)
    risk_profile = _read_json(risk_profile_path)
    intent = _read_json(intent_path)

    governance_status = _normalize_governance_status(governance)
    security_status = _normalize_upper(
        security.get("status") or security.get("security_status"),
        "UNKNOWN",
    )
    ops_mode = _normalize_upper(ops.get("mode") or ops.get("ops_mode"), "UNKNOWN")

    return GateInput(
        governance_status=governance_status,
        security_status=security_status,
        ops_mode=ops_mode,
        risk_profile=risk_profile,
        intent=intent,
    )


def evaluate_gate(data: GateInput) -> dict[str, Any]:
    reasons: list[str] = []

    if data.governance_status not in DEFAULT_ALLOWED_GOVERNANCE:
        reasons.append(
            f"blocked_by_governance_status:{data.governance_status}"
        )
    if data.security_status not in DEFAULT_ALLOWED_SECURITY:
        reasons.append(f"blocked_by_security_status:{data.security_status}")
    if data.ops_mode in DEFAULT_BLOCKED_OPS_MODES:
        reasons.append(f"blocked_by_ops_mode:{data.ops_mode}")

    governance_bridge = data.risk_profile.get("governance_bridge", {})
    if isinstance(governance_bridge, dict):
        final_allowed = governance_bridge.get("final_action_allowed")
        if final_allowed is False:
            reasons.append("blocked_by_risk_governance_bridge_final_action:false")
    qty = data.intent.get("qty")
    max_position = data.risk_profile.get("max_position_size")
    try:
        if qty is not None and max_position is not None and float(qty) > float(max_position):
            reasons.append(f"blocked_by_risk_max_position_size:{qty}>{max_position}")
    except (TypeError, ValueError):
        pass
    leverage_cap = data.risk_profile.get("leverage_multiplier_cap")
    requested_leverage = data.intent.get("leverage")
    if requested_leverage is None and isinstance(data.intent.get("extra"), dict):
        requested_leverage = data.intent["extra"].get("leverage")
    try:
        if requested_leverage is not None and leverage_cap is not None and float(requested_leverage) > float(leverage_cap):
            reasons.append(f"blocked_by_risk_leverage_cap:{requested_leverage}>{leverage_cap}")
    except (TypeError, ValueError):
        pass

    allow = len(reasons) == 0
    return {
        "schema": "execution_gate_decision_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "allow_order": allow,
        "decision": "ALLOW" if allow else "BLOCK",
        "reasons": reasons,
        "inputs": {
            "governance_status": data.governance_status,
            "security_status": data.security_status,
            "ops_mode": data.ops_mode,
            "risk_profile_source": data.risk_profile.get("source", ""),
            "risk_profile_mode": data.risk_profile.get("mode", ""),
        },
        "intent_summary": {
            "symbol": data.intent.get("symbol", ""),
            "side": data.intent.get("side", ""),
            "qty": data.intent.get("qty", ""),
            "request_id": data.intent.get("request_id", ""),
        },
    }


def append_audit_log(result: dict[str, Any], audit_path: Path) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "execution_gate_audit_v1",
        "ts_utc": result.get("ts_utc"),
        "decision": result.get("decision"),
        "allow_order": result.get("allow_order"),
        "reasons": result.get("reasons", []),
        "inputs": result.get("inputs", {}),
        "intent_summary": result.get("intent_summary", {}),
    }
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def maybe_send_webhook(result: dict[str, Any], webhook_url: str) -> None:
    if not webhook_url.strip():
        return
    body = json.dumps(
        {
            "schema": "execution_gate_alert_v1",
            "ts_utc": result.get("ts_utc"),
            "decision": result.get("decision"),
            "allow_order": result.get("allow_order"),
            "reasons": result.get("reasons", []),
            "inputs": result.get("inputs", {}),
            "intent_summary": result.get("intent_summary", {}),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8):
        return


def _read_dotenv_value(dotenv_path: Path, key: str) -> str:
    if not dotenv_path.exists():
        return ""
    prefix = f"{key}="
    try:
        for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or not line.startswith(prefix):
                continue
            value = line[len(prefix):].strip()
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value.strip()
    except Exception:
        return ""
    return ""


def _resolve_webhook_url(cli_webhook: str) -> str:
    if cli_webhook.strip():
        return cli_webhook.strip()
    env_value = os.getenv("EXECUTION_GATE_ALERT_WEBHOOK_URL", "").strip()
    if env_value:
        return env_value

    workspace = Path(__file__).resolve().parents[1]
    dotenv = workspace / ".env"
    dot_value = _read_dotenv_value(dotenv, "EXECUTION_GATE_ALERT_WEBHOOK_URL")
    if dot_value:
        return dot_value
    # Fallback to existing workspace-wide alarm channel if dedicated webhook is not set.
    fallback = os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    if fallback:
        return fallback
    return _read_dotenv_value(dotenv, "OPS_ALARM_WEBHOOK_URL")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centralized execution gate for trade intents."
    )
    parser.add_argument(
        "--governance-path",
        default="docs/final/artifacts/integrated_governance_v1_latest.json",
        help="Governance status JSON path.",
    )
    parser.add_argument(
        "--security-status-path",
        default="reports/security_integrity_status_latest.json",
        help="Security monitor status JSON path.",
    )
    parser.add_argument(
        "--ops-status-path",
        default="reports/athena_ops_status_latest.json",
        help="Ops monitor status JSON path.",
    )
    parser.add_argument(
        "--risk-profile-path",
        default="projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
        help="Risk profile JSON path for max position / governance bridge checks.",
    )
    parser.add_argument(
        "--intent-path",
        required=True,
        help="Incoming order intent JSON path.",
    )
    parser.add_argument(
        "--output-path",
        default="reports/execution_gate_decision_latest.json",
        help="Decision output JSON path.",
    )
    parser.add_argument(
        "--audit-jsonl",
        default="reports/execution_gate_audit_log.jsonl",
        help="Append-only gate audit JSONL path.",
    )
    parser.add_argument(
        "--alert-webhook-url",
        default="",
        help="Optional webhook URL for decision alerts. If empty, use EXECUTION_GATE_ALERT_WEBHOOK_URL env when set.",
    )
    parser.add_argument(
        "--alert-on",
        choices=("all", "block"),
        default="block",
        help="Webhook alert policy. Default sends only BLOCK decisions.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = _load_gate_input(
        governance_path=Path(args.governance_path),
        security_status_path=Path(args.security_status_path),
        ops_status_path=Path(args.ops_status_path),
        risk_profile_path=Path(args.risk_profile_path),
        intent_path=Path(args.intent_path),
    )
    result = evaluate_gate(data)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_audit_log(result, Path(args.audit_jsonl))
    webhook = _resolve_webhook_url(args.alert_webhook_url)
    should_alert = bool(webhook) and (
        args.alert_on == "all" or result["decision"] == "BLOCK"
    )
    if should_alert:
        try:
            maybe_send_webhook(result, webhook)
        except (urllib.error.URLError, TimeoutError):
            # Gate decision must remain deterministic even if alert delivery fails.
            pass
    print(
        f"execution_gate_decision={result['decision']} output_path={output_path.as_posix()}"
    )
    return 0 if result["allow_order"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
