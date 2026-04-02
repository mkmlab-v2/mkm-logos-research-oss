#!/usr/bin/env python3
"""Send Slack alert when verify_all_green detects a failure.

Safety:
- Default is dry-run unless --live is passed OR ALL_GREEN_SLACK_LIVE env is truthy.
- Works with the existing Slack webhook envs used elsewhere in this repo.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ALL_GREEN_JSON = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "all_green_latest.json"
DEFAULT_OUT_LATEST = ROOT / "docs" / "final" / "artifacts" / "all_green_slack_failure_latest.json"
DEFAULT_LOG_JSONL = ROOT / "docs" / "final" / "artifacts" / "all_green_slack_failure_delivery_log.jsonl"

DOTENV_PATH = ROOT / ".env"


def _load_env_from_dotenv(path: Path) -> None:
    if not path.exists():
        return
    # Keep process env precedence.
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k in os.environ:
            continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
            v = v[1:-1]
        os.environ[k] = v


def _truthy(x: str | None) -> bool:
    if x is None:
        return False
    return str(x).strip().lower() in {"1", "true", "yes", "y", "on"}


def _webhook_url() -> str:
    return (
        os.getenv("ALL_GREEN_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def _mask_webhook(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 12:
        return "***"
    return url[:6] + "***" + url[-6:]


def _safe_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _append_log(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_slack_text(all_green: Dict[str, Any]) -> str:
    ts = all_green.get("ts_utc") or datetime.now(timezone.utc).isoformat()
    steps: List[Dict[str, Any]] = all_green.get("steps") or []
    failed = [s for s in steps if not s.get("ok")]
    failed_names = [str(s.get("step")) for s in failed if s.get("step") is not None]
    failed_line = ", ".join(failed_names) if failed_names else "unknown_failure"

    lines = [
        ":rotating_light: *ALL-GREEN FAILED*",
        f"- ts_utc: {ts}",
        f"- failed_steps: {failed_line}",
    ]
    # Include minimal exit codes for operator triage.
    for s in failed[:6]:
        step = str(s.get("step") or "")
        code = s.get("exit_code")
        lines.append(f"- {step}: exit_code={code}")
    return "\n".join(lines)


def _post_to_slack(webhook: str, text: str, timeout_s: int = 15) -> None:
    data = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read().decode("utf-8", errors="ignore")
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def _post_with_retry(webhook: str, text: str, timeout_s: int, max_retries: int, backoff_s: float) -> None:
    attempts = max(1, int(max_retries) + 1)
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            _post_to_slack(webhook, text, timeout_s=timeout_s)
            return
        except Exception as exc:  # noqa: BLE001 - keep sender robust in runtime scripts
            last_err = exc
            if i >= attempts - 1:
                break
            time.sleep(max(0.0, float(backoff_s)) * (i + 1))
    if last_err is not None:
        raise RuntimeError(f"Slack send failed after retries: {last_err}") from last_err


def main() -> int:
    p = argparse.ArgumentParser(description="Send Slack alert for verify_all_green failure.")
    p.add_argument("--all-green-json", default=str(DEFAULT_ALL_GREEN_JSON))
    p.add_argument("--dry-run", action="store_true", help="Do not send webhook; write evidence only.")
    p.add_argument("--live", action="store_true", help="Force live sending even in dry-run mode.")
    p.add_argument("--timeout-s", type=int, default=15)
    p.add_argument("--max-retries", type=int, default=2, help="Additional retries after first attempt (default: 2 => total 3 tries).")
    p.add_argument("--backoff-s", type=float, default=2.0, help="Base backoff seconds between retries.")
    args = p.parse_args()

    _load_env_from_dotenv(DOTENV_PATH)

    live_env = _truthy(os.getenv("ALL_GREEN_SLACK_LIVE"))
    send_live = bool(args.live) or live_env
    if args.dry_run:
        send_live = False

    all_green = _safe_json(Path(args.all_green_json))
    text = _build_slack_text(all_green)

    webhook = _webhook_url()
    record: Dict[str, Any] = {
        "schema": "all_green_slack_failure_delivery_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "attempt",
        "input_all_green_path": str(Path(args.all_green_json).resolve()),
        "webhook_url_masked": _mask_webhook(webhook),
        "dry_run": not send_live,
        "webhook_sent": False,
        "final": False,
        "text_preview": text[:600],
    }

    # Always write evidence.
    DEFAULT_OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(DEFAULT_LOG_JSONL, record)

    if not send_live:
        record["phase"] = "final"
        record["final"] = True
        print("[all-green-slack] dry-run: not sending Slack webhook")
        DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_log(DEFAULT_LOG_JSONL, record)
        return 0

    if not webhook:
        raise SystemExit("Slack webhook URL not set (ALL_GREEN_SLACK_WEBHOOK_URL / FACT_SAFE_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL)")

    _post_with_retry(
        webhook=webhook,
        text=text,
        timeout_s=int(args.timeout_s),
        max_retries=int(args.max_retries),
        backoff_s=float(args.backoff_s),
    )
    record["phase"] = "final"
    record["final"] = True
    record["webhook_sent"] = True
    DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(DEFAULT_LOG_JSONL, record)
    print("[all-green-slack] sent Slack webhook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

