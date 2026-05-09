#!/usr/bin/env python3
"""Emit alerts when trading observation status transitions to risky states."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIEF = ROOT / "docs" / "final" / "artifacts" / "trading_observation_brief_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "trading_observation_alert_state_latest.json"
DEFAULT_LOG = ROOT / "docs" / "final" / "artifacts" / "trading_observation_alert_log.jsonl"
DOTENV_PATH = ROOT / ".env"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if " #" in v:
            v = v.split(" #", 1)[0].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
            v = v[1:-1]
        if k and k not in os.environ:
            os.environ[k] = v


def _webhook_url() -> str:
    return (
        os.getenv("TRADING_OBS_ALERT_WEBHOOK_URL", "").strip()
        or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def _post(webhook: str, text: str, timeout_s: int) -> None:
    payload = {"text": text}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read()
    except error.URLError as exc:
        raise RuntimeError(f"webhook post failed: {exc}") from exc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief", type=Path, default=DEFAULT_BRIEF)
    ap.add_argument("--state", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--timeout-s", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    brief_path = args.brief if args.brief.is_absolute() else (ROOT / args.brief)
    state_path = args.state if args.state.is_absolute() else (ROOT / args.state)
    log_path = args.log if args.log.is_absolute() else (ROOT / args.log)

    brief = _load_json(brief_path)
    if brief is None:
        row = {
            "schema": "trading_observation_alert_v1",
            "ts_utc": _utc_now(),
            "status": "error",
            "error": "missing_or_invalid_brief",
            "brief_path": str(brief_path),
        }
        _append_jsonl(log_path, row)
        print("ALERT_CHECK_ERROR: missing_or_invalid_brief")
        return 1

    prev = _load_json(state_path) or {}
    curr_go = str(brief.get("go_no_go") or "UNKNOWN")
    curr_cov = str(brief.get("protective_coverage_status") or "unknown")
    curr_promo = bool(brief.get("promotion_ready") is True)
    curr_summary = str(brief.get("summary_line") or "")

    prev_go = str(prev.get("go_no_go") or "UNKNOWN")
    prev_cov = str(prev.get("protective_coverage_status") or "unknown")
    prev_promo = bool(prev.get("promotion_ready") is True)

    alerts: list[str] = []
    if prev_go == "GO" and curr_go != "GO":
        alerts.append(f"go_no_go_transition: {prev_go}->{curr_go}")
    if prev_cov == "covered" and curr_cov != "covered":
        alerts.append(f"coverage_transition: {prev_cov}->{curr_cov}")
    if curr_go != "GO":
        alerts.append(f"go_no_go_current_not_go: {curr_go}")
    if curr_cov != "covered":
        alerts.append(f"coverage_current_not_covered: {curr_cov}")
    if prev_promo != curr_promo:
        alerts.append(f"promotion_ready_transition: {prev_promo}->{curr_promo}")

    state_doc = {
        "schema": "trading_observation_alert_state_v1",
        "updated_at_utc": _utc_now(),
        "go_no_go": curr_go,
        "protective_coverage_status": curr_cov,
        "promotion_ready": curr_promo,
        "summary_line": curr_summary,
    }
    _write_json(state_path, state_doc)

    row: dict[str, Any] = {
        "schema": "trading_observation_alert_v1",
        "ts_utc": _utc_now(),
        "status": "ok",
        "alerts": alerts,
        "brief_path": str(brief_path),
        "state_path": str(state_path),
        "summary_line": curr_summary,
    }

    _load_env(DOTENV_PATH)
    webhook = _webhook_url()
    if alerts and webhook and not args.dry_run:
        msg = "[Trading Observation Alert]\n" + "\n".join(f"- {a}" for a in alerts) + f"\n{curr_summary}"
        try:
            _post(webhook, msg, timeout_s=int(args.timeout_s))
            row["webhook_sent"] = True
        except RuntimeError as exc:
            row["webhook_sent"] = False
            row["webhook_error"] = str(exc)
    else:
        row["webhook_sent"] = False
        row["webhook_skipped"] = True
        row["webhook_reason"] = "no_alerts_or_no_webhook_or_dry_run"

    _append_jsonl(log_path, row)
    if alerts:
        print("ALERTS: " + " | ".join(alerts))
    else:
        print("ALERTS: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
