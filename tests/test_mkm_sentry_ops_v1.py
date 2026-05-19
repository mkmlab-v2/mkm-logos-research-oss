from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "mkm_sentry_ops_v1",
        ROOT / "scripts/mkm_sentry_ops_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_sentry_disabled_without_dsn(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    mod = _load_mod()
    assert mod.sentry_enabled() is False
    assert mod.init_sentry_ops(script="test") is False


def test_run_cron_job_passthrough_without_dsn(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    mod = _load_mod()
    assert mod.run_cron_job("slug", lambda: 7, script="test") == 7
