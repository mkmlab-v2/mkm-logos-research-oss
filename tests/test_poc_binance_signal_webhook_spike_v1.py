# -*- coding: utf-8 -*-
"""poc_binance_signal_webhook_spike_v1.py — dry-run + mocked POST, no network."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "projects" / "bitcoin-trading" / "scripts" / "poc_binance_signal_webhook_spike_v1.py"
EXAMPLE = ROOT / "docs" / "final" / "artifacts" / "examples" / "poc_binance_signal_webhook_payload_v1.example.json"


def _run(*args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
        env=full_env,
    )


def test_script_and_example_exist():
    assert SCRIPT.is_file(), SCRIPT
    assert EXAMPLE.is_file(), EXAMPLE


def test_dry_run_writes_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    out = tmp_path / "summary.json"
    r = _run(
        "--dry-run",
        "--payload-file",
        str(EXAMPLE),
        "--out",
        str(out),
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "poc_binance_signal_webhook_spike_summary_v1"
    assert data.get("ok") is True
    assert "target_host_redacted" in data


def test_live_post_missing_url_fails(tmp_path: Path):
    out = tmp_path / "summary.json"
    env = {"BINANCE_USDM_SIGNAL_WEBHOOK_URL": ""}
    r = _run("--payload-file", str(EXAMPLE), "--out", str(out), env=env)
    assert r.returncode == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("ok") is False
    assert data.get("error") == "missing_url"


def test_live_post_success_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import urllib.request

    out = tmp_path / "summary.json"

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n: int = -1):
            return b'{"ok":true}'

    def _fake_urlopen(req, timeout=None):
        assert req.get_method() == "POST"
        assert req.full_url == "https://example.invalid/webhook-test"
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    import importlib.util

    spec = importlib.util.spec_from_file_location("poc_spike", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setenv("BINANCE_USDM_SIGNAL_WEBHOOK_URL", "https://example.invalid/webhook-test")
    code = mod.main(
        [
            "--payload-file",
            str(EXAMPLE),
            "--out",
            str(out),
            "--timeout",
            "5",
        ]
    )
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("ok") is True
    assert data.get("http_status") == 200
