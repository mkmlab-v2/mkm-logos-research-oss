"""Unit tests for send_cross_lens_rag_alert_v1 (stale guard, status filter, dedupe)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "send_cross_lens_rag_alert_v1.py"


def _run(
    tmp: Path,
    *,
    fusion: dict,
    alert: dict | None,
    state: dict | None = None,
    extra_args: list[str] | None = None,
    env_extra: dict[str, str] | None = None,
) -> dict:
    fusion_p = tmp / "fusion.json"
    alert_p = tmp / "alert.json"
    state_p = tmp / "state.json"
    out_p = tmp / "result.json"
    fusion_p.write_text(json.dumps(fusion), encoding="utf-8")
    if alert is not None:
        alert_p.write_text(json.dumps(alert), encoding="utf-8")
    if state is not None:
        state_p.write_text(json.dumps(state), encoding="utf-8")
    env = os.environ.copy()
    env.pop("CROSS_LENS_RAG_ALERT_WEBHOOK_URL", None)
    env.pop("OPS_ALARM_WEBHOOK_URL", None)
    for k in (
        "CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS",
        "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    args = [
        sys.executable,
        str(SCRIPT),
        "--fusion-json",
        str(fusion_p),
        "--alert-json",
        str(alert_p),
        "--state-json",
        str(state_p),
        "--output-json",
        str(out_p),
    ]
    args.append("--no-dotenv")
    if extra_args:
        args.extend(extra_args)
    r = subprocess.run(args, cwd=str(ROOT), env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    return json.loads(out_p.read_text(encoding="utf-8"))


def test_stale_alert_ts_skipped(tmp_path: Path) -> None:
    fusion = {"ts_utc": "2026-05-09T12:00:00Z"}
    alert = {"ts_utc": "2026-05-08T10:00:00Z", "status": "YELLOW", "schema": "cross_lens_rag_alert_v1"}
    doc = _run(tmp_path, fusion=fusion, alert=alert)
    assert doc["notify_skipped_reason"] == "alert_not_refreshed_this_fusion_run"


def test_yellow_would_notify_but_no_channel(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "YELLOW",
        "always_emit": False,
        "signal_light": {"status": "YELLOW"},
    }
    doc = _run(tmp_path, fusion=fusion, alert=alert)
    assert doc["notify_skipped_reason"] == "no_delivery_channel_configured"


def test_green_filtered_without_include_green(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "GREEN",
        "always_emit": False,
        "signal_light": {"status": "GREEN"},
    }
    doc = _run(tmp_path, fusion=fusion, alert=alert)
    assert doc["notify_skipped_reason"] == "status_filtered"


def test_green_heartbeat_webhook_ok_telegram_skipped(tmp_path: Path) -> None:
    """GREEN always_emit posts to webhook only; Telegram never sends GREEN."""
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "GREEN",
        "always_emit": True,
        "signal_light": {"status": "GREEN"},
    }
    doc = _run(
        tmp_path,
        fusion=fusion,
        alert=alert,
        extra_args=["--dry-run"],
        env_extra={
            "CROSS_LENS_RAG_ALERT_WEBHOOK_URL": "https://example.invalid/hook",
            "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY": "1",
            "TELEGRAM_BOT_TOKEN": "fake-token",
            "TELEGRAM_CHAT_ID": "12345",
        },
    )
    assert doc.get("notify_skipped_reason") is None
    assert doc["webhook_result"] == "dry_run"
    assert doc["telegram_result"] == "skipped_non_important_for_telegram"


def test_green_always_emit_requires_channel(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "GREEN",
        "always_emit": True,
        "signal_light": {"status": "GREEN"},
    }
    doc = _run(tmp_path, fusion=fusion, alert=alert)
    assert doc["notify_skipped_reason"] == "no_delivery_channel_configured"


def test_dedupe_same_ts(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "RED",
        "signal_light": {"status": "RED"},
    }
    state = {"last_notified_ts_utc": ts}
    doc = _run(tmp_path, fusion=fusion, alert=alert, state=state)
    assert doc["notify_skipped_reason"] == "already_notified_this_alert_ts"


def test_yellow_webhook_dry_run_telegram_skipped_below_red_min(tmp_path: Path) -> None:
    """Default Telegram min is RED; YELLOW does not ping Telegram."""
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "YELLOW",
        "signal_light": {"status": "YELLOW"},
    }
    doc = _run(
        tmp_path,
        fusion=fusion,
        alert=alert,
        extra_args=["--dry-run"],
        env_extra={
            "CROSS_LENS_RAG_ALERT_WEBHOOK_URL": "https://example.invalid/hook",
            "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY": "1",
            "TELEGRAM_BOT_TOKEN": "fake-token",
            "TELEGRAM_CHAT_ID": "12345",
        },
    )
    assert doc["telegram_min_status"] == "red"
    assert doc["webhook_result"] == "dry_run"
    assert doc["telegram_result"] == "skipped_below_telegram_min_status"


def test_yellow_telegram_only_when_min_status_yellow(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "YELLOW",
        "signal_light": {"status": "YELLOW"},
    }
    doc = _run(
        tmp_path,
        fusion=fusion,
        alert=alert,
        extra_args=["--dry-run", "--telegram-min-status", "yellow"],
        env_extra={
            "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY": "1",
            "TELEGRAM_BOT_TOKEN": "fake-token",
            "TELEGRAM_CHAT_ID": "12345",
        },
    )
    assert doc["telegram_min_status"] == "yellow"
    assert doc["webhook_result"] == "no_webhook_configured"
    assert doc["telegram_result"] == "dry_run"


def test_yellow_red_only_policy_no_webhook_implies_no_delivery(tmp_path: Path) -> None:
    """YELLOW + Telegram credentials but RED-only default + no webhook → cannot deliver."""
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "YELLOW",
        "signal_light": {"status": "YELLOW"},
    }
    doc = _run(
        tmp_path,
        fusion=fusion,
        alert=alert,
        env_extra={
            "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY": "1",
            "TELEGRAM_BOT_TOKEN": "fake-token",
            "TELEGRAM_CHAT_ID": "12345",
            "CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS": "red",
        },
    )
    assert doc["notify_skipped_reason"] == "no_delivery_channel_configured"
    assert doc["telegram_min_status"] == "red"


def test_force_bypasses_dedupe(tmp_path: Path) -> None:
    ts = "2026-05-09T12:00:00Z"
    fusion = {"ts_utc": ts}
    alert = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": ts,
        "status": "RED",
        "signal_light": {"status": "RED"},
    }
    state = {"last_notified_ts_utc": ts}
    doc = _run(tmp_path, fusion=fusion, alert=alert, state=state, extra_args=["--force"])
    assert doc["notify_skipped_reason"] == "no_delivery_channel_configured"
