#!/usr/bin/env python3
"""Optional Sentry ops helper (errors + crons). No-op when SENTRY_DSN unset or sentry-sdk missing."""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_ENV_LOADED = False
_INITIALIZED = False


def _load_workspace_dotenv() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key.startswith("SENTRY_"):
            continue
        if key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def sentry_enabled() -> bool:
    try:
        import sentry_sdk  # noqa: F401
    except ImportError:
        return False
    _load_workspace_dotenv()
    return bool(os.environ.get("SENTRY_DSN", "").strip())


def init_sentry_ops(*, script: str, **tags: str) -> bool:
    """Initialize Sentry for batch/ops scripts. Returns True when active."""
    global _INITIALIZED
    if _INITIALIZED:
        return sentry_enabled()
    _load_workspace_dotenv()
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        return False

    environment = os.environ.get("SENTRY_ENVIRONMENT", "local").strip() or "local"
    release = os.environ.get("SENTRY_RELEASE", "").strip() or None
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("mkm.script", script)
        for key, value in tags.items():
            scope.set_tag(key, value)
    _INITIALIZED = True
    return True


def run_cron_job(
    monitor_slug: str,
    fn: Callable[[], int],
    *,
    script: str,
    monitor_config: dict[str, Any] | None = None,
    **tags: str,
) -> int:
    """Run fn under Sentry Crons when DSN is configured; otherwise call fn directly."""
    if not init_sentry_ops(script=script, **tags):
        return fn()

    from sentry_sdk.crons import monitor

    cfg = monitor_config or {
        "schedule": {"type": "crontab", "value": "0 6 * * *"},
        "timezone": "Asia/Seoul",
        "checkin_margin": 30,
        "max_runtime": 15,
    }
    with monitor(monitor_slug=monitor_slug, monitor_config=cfg):
        return fn()


def capture_ops_health_failure(*, script: str, doc: dict[str, Any]) -> None:
    """Report structured health JSON failure (exit 1 without exception)."""
    if not doc.get("ok") and init_sentry_ops(script=script):
        import sentry_sdk

        failed: list[str] = []
        checks = doc.get("checks") or {}
        if isinstance(checks, dict):
            for name, row in checks.items():
                if isinstance(row, dict) and row.get("ok") is False:
                    failed.append(str(name))
        sentry_sdk.set_context(
            "health",
            {
                "schema": doc.get("schema"),
                "strict_mode": doc.get("strict_mode"),
                "failed_checks": failed,
                "recommended_next": doc.get("recommended_next"),
            },
        )
        sentry_sdk.capture_message(
            f"{script}: sandbox health check failed",
            level="error",
            fingerprint=[script, "health-failed", doc.get("schema") or "unknown"],
        )
