from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_iso(ts: str) -> datetime | None:
    text = str(ts or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Build single-file trading guardian ops snapshot.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--output-json", default="reports/trading_guardian_ops_snapshot_latest.json")
    args = p.parse_args()

    root = Path(args.workspace_root).resolve()
    bundle = _read_json(root / "reports" / "trading_guardian_bundle_status_latest.json")
    alert_state = _read_json(root / "reports" / "trading_guardian_bundle_alert_state_latest.json")
    policy = _read_json(root / "reports" / "trading_guardian_policy_latest.json")

    cooldown_h = 0.5
    p_alert = policy.get("guardian_bundle_alert")
    if isinstance(p_alert, dict):
        try:
            cooldown_h = float(p_alert.get("cooldown_hours", cooldown_h))
        except (TypeError, ValueError):
            pass

    last_sent_dt = _parse_iso(str(alert_state.get("last_sent_at_utc", "")))
    cooldown_expires_at = None
    cooldown_remaining_minutes = 0.0
    if last_sent_dt is not None:
        exp = last_sent_dt + timedelta(hours=max(0.0, cooldown_h))
        now = datetime.now(timezone.utc)
        cooldown_expires_at = exp.isoformat()
        cooldown_remaining_minutes = max(0.0, (exp - now).total_seconds() / 60.0)

    payload = {
        "schema": "trading_guardian_ops_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": bundle.get("status", "UNKNOWN"),
        "ok": bundle.get("ok", False),
        "bundle": bundle,
        "alert_state": alert_state,
        "policy": {
            "guardian_bundle_alert": {"cooldown_hours": cooldown_h},
            "protective_guard": policy.get("protective_guard", {}),
        },
        "cooldown": {
            "expires_at_utc": cooldown_expires_at,
            "remaining_minutes": round(cooldown_remaining_minutes, 3),
        },
    }

    out = root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"trading_guardian_ops_snapshot_written={out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
