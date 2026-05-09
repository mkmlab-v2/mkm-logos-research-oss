from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run non-destructive daily drill for trading guardian alert flow.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--cooldown-hours", type=float, default=0.5)
    p.add_argument("--output-json", default="reports/trading_guardian_daily_drill_latest.json")
    return p.parse_args()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    merged = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode, merged.strip()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).resolve()
    tmp_bundle = root / "reports" / "trading_guardian_bundle_status_drill_tmp.json"
    tmp_state = root / "reports" / "trading_guardian_bundle_alert_state_drill_tmp.json"
    out_json = root / args.output_json

    payload = {
        "schema": "trading_guardian_bundle_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DEGRADED",
        "ok": False,
        "components": {
            "trading_automation_health": {"go_no_go": "HOLD", "ok": False},
            "protective_coverage": {
                "status": "uncovered",
                "symbol": "BTCUSDT",
                "position": {"side": "SHORT"},
            },
        },
    }
    _write_json(tmp_bundle, payload)

    cmd = [
        sys.executable,
        str(root / "scripts" / "send_trading_guardian_bundle_alert_v1.py"),
        "--workspace-root",
        str(root),
        "--bundle-json",
        "reports/trading_guardian_bundle_status_drill_tmp.json",
        "--state-json",
        "reports/trading_guardian_bundle_alert_state_drill_tmp.json",
        "--cooldown-hours",
        str(args.cooldown_hours),
    ]
    first_code, first_out = _run(cmd, root)
    second_code, second_out = _run(cmd, root)

    result = {
        "schema": "trading_guardian_daily_drill_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cooldown_hours": float(args.cooldown_hours),
        "first_run": {"exit_code": first_code, "output": first_out},
        "second_run": {"exit_code": second_code, "output": second_out},
        "ok": (
            first_code == 0
            and second_code == 0
            and "trading_guardian_bundle_alert_sent=true" in first_out
            and "trading_guardian_bundle_alert_skipped=cooldown" in second_out
        ),
    }
    _write_json(out_json, result)

    try:
        tmp_bundle.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        tmp_state.unlink(missing_ok=True)
    except OSError:
        pass

    print(f"trading_guardian_daily_drill_written={out_json.as_posix()}")
    print(f"trading_guardian_daily_drill_ok={str(result['ok']).lower()}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
