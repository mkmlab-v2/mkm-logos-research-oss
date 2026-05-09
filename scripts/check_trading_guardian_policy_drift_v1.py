from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check/snapshot trading guardian policy hash drift.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--policy-json", default="reports/trading_guardian_policy_latest.json")
    p.add_argument("--state-json", default="reports/trading_guardian_policy_hash_state_latest.json")
    p.add_argument("--mode", choices=("check", "snapshot"), default="check")
    return p.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).resolve()
    policy_path = root / args.policy_json
    state_path = root / args.state_json
    now = datetime.now(timezone.utc).isoformat()

    if not policy_path.exists():
        out = {
            "schema": "trading_guardian_policy_drift_v1",
            "generated_at_utc": now,
            "mode": args.mode,
            "status": "missing_policy",
            "ok": False,
            "policy_path": str(policy_path).replace("\\", "/"),
        }
        _write(state_path, out)
        print("trading_guardian_policy_drift_status=missing_policy")
        return 2

    policy_hash = _sha256(policy_path)
    prev = _read_json(state_path)
    baseline_hash = str(prev.get("baseline_sha256", "")).strip()

    if args.mode == "snapshot" or not baseline_hash:
        out = {
            "schema": "trading_guardian_policy_drift_v1",
            "generated_at_utc": now,
            "mode": "snapshot",
            "status": "baseline_updated",
            "ok": True,
            "policy_path": str(policy_path).replace("\\", "/"),
            "baseline_sha256": policy_hash,
            "current_sha256": policy_hash,
            "drift_detected": False,
        }
        _write(state_path, out)
        print("trading_guardian_policy_drift_status=baseline_updated")
        return 0

    drift = policy_hash != baseline_hash
    out = {
        "schema": "trading_guardian_policy_drift_v1",
        "generated_at_utc": now,
        "mode": "check",
        "status": "drift" if drift else "in_sync",
        "ok": not drift,
        "policy_path": str(policy_path).replace("\\", "/"),
        "baseline_sha256": baseline_hash,
        "current_sha256": policy_hash,
        "drift_detected": drift,
    }
    _write(state_path, out)
    print(f"trading_guardian_policy_drift_status={out['status']}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
