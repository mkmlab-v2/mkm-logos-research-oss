#!/usr/bin/env python3
"""Alert when prophecy guard profile transitions between runs."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISION = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_decision_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_profile_state_latest.json"
DEFAULT_ALERT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_profile_transition_alert_latest.json"
DEFAULT_TRANSITION_LOG = ROOT / "reports" / "prophecy_causal_active_guard_profile_transition_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Alert when guard policy profile changes.")
    ap.add_argument("--decision-json", type=Path, default=DEFAULT_DECISION)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--out-alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--append-transition-log-jsonl", type=Path, default=DEFAULT_TRANSITION_LOG)
    args = ap.parse_args()

    decision_path = args.decision_json if args.decision_json.is_absolute() else ROOT / args.decision_json
    state_path = args.state_json if args.state_json.is_absolute() else ROOT / args.state_json
    out_alert_path = args.out_alert_json if args.out_alert_json.is_absolute() else ROOT / args.out_alert_json
    transition_log_path = (
        args.append_transition_log_jsonl
        if args.append_transition_log_jsonl.is_absolute()
        else ROOT / args.append_transition_log_jsonl
    )

    decision = _load(decision_path)
    state = _load(state_path)
    new_profile = str(decision.get("selected_profile") or "").strip()
    prev_profile = str(state.get("selected_profile") or "").strip()
    transitioned = bool(prev_profile and new_profile and prev_profile != new_profile)

    webhook_url = os.getenv("MKM_PROPHECY_PROFILE_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or ""
    notified = False
    notify_status = "skipped_no_transition"
    if transitioned:
        payload = {
            "event": "prophecy_guard_profile_transition_v1",
            "generated_at_utc": _now(),
            "previous_profile": prev_profile,
            "current_profile": new_profile,
            "observed_hit_rate": decision.get("observed_hit_rate"),
            "observed_walkforward_mean_test_accuracy": decision.get("observed_walkforward_mean_test_accuracy"),
            "decision_json": str(decision_path),
        }
        if webhook_url:
            ok, status = _post_webhook(webhook_url, payload)
            notified = ok
            notify_status = status if ok else f"failed:{status}"
        else:
            notify_status = "skipped_no_webhook"

    state_out = {
        "schema": "prophecy_causal_active_guard_profile_state_v1",
        "updated_at_utc": _now(),
        "selected_profile": new_profile,
        "decision_json": str(decision_path),
    }
    _write(state_path, state_out)

    out = {
        "schema": "prophecy_causal_active_guard_profile_transition_alert_v1",
        "generated_at_utc": _now(),
        "previous_profile": prev_profile or None,
        "current_profile": new_profile or None,
        "transitioned": transitioned,
        "notified": notified,
        "notify_status": notify_status,
        "state_json": str(state_path),
        "decision_json": str(decision_path),
    }

    # Backfill transition metadata into the latest decision artifact
    # so downstream readers can inspect profile switching without joining files.
    if isinstance(decision, dict):
        decision["transition_checked_at_utc"] = _now()
        decision["previous_profile"] = prev_profile or None
        decision["transitioned"] = transitioned
        decision["notification_status"] = notify_status
        decision["notification_sent"] = notified
        _write(decision_path, decision)

    _write(out_alert_path, out)
    _append_jsonl(transition_log_path, out)
    print(f"WROTE: {state_path.resolve()}")
    print(f"WROTE: {decision_path.resolve()}")
    print(f"WROTE: {out_alert_path.resolve()}")
    print(f"APPEND: {transition_log_path.resolve()}")
    print(f"transitioned={transitioned} notified={notified} status={notify_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
