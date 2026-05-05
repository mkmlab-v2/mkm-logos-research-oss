# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def test_trade_execute_denied_when_governance_hold(tmp_path):
    fixture = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"
    ecc_out = tmp_path / "ecc.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "athena_run_v1.py"),
            "--governance-json",
            str(fixture),
            "--ecc-out",
            str(ecc_out),
            "--no-audit-append",
            "--",
            sys.executable,
            str(_REPO / "scripts" / "trade_dummy.py"),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "ECC DENIED: Governance is in HOLD mode." in proc.stderr
    doc = json.loads(ecc_out.read_text(encoding="utf-8"))
    assert doc["status"] == "DENIED"
    assert doc["reason"] == "governance_hold_trade_execute"


def test_observe_only_runs_without_secret_even_under_hold(tmp_path):
    fixture = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"
    ecc_out = tmp_path / "ecc.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "athena_run_v1.py"),
            "--governance-json",
            str(fixture),
            "--ecc-out",
            str(ecc_out),
            "--no-audit-append",
            "--action",
            "OBSERVE_ONLY",
            "--",
            sys.executable,
            "-c",
            "print('observe_ok')",
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "observe_ok" in proc.stdout
    doc = json.loads(ecc_out.read_text(encoding="utf-8"))
    assert doc["status"] == "APPROVED"


def test_trade_execute_with_target_injects_from_resolve(monkeypatch, tmp_path):
    attack = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_attack.json"
    ecc_out = tmp_path / "ecc.json"

    def _fake_resolve(name: str):
        return "from_dpapi" if name == "BINANCE_API_KEY" else None

    monkeypatch.setattr("scripts.athena_run_v1._resolve_secret", _fake_resolve)

    from scripts.athena_run_v1 import main

    rc = main(
        [
            "--governance-json",
            str(attack),
            "--ecc-out",
            str(ecc_out),
            "--no-default-integrity-path",
            "--no-audit-append",
            "--target",
            "BINANCE_API_KEY",
            "--",
            sys.executable,
            "-c",
            "import os,sys; v=os.environ.get('BINANCE_API_KEY',''); sys.exit(0 if v=='from_dpapi' else 1)",
        ]
    )
    assert rc == 0
    doc = json.loads(ecc_out.read_text(encoding="utf-8"))
    assert doc["status"] == "APPROVED"
    assert "dpapi_in_flight" in doc["audit_ref"]


def test_trade_execute_target_missing_key_exits_1(monkeypatch, tmp_path):
    attack = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_attack.json"
    ecc_out = tmp_path / "ecc.json"

    monkeypatch.setattr("scripts.athena_run_v1._resolve_secret", lambda name: None)

    from scripts.athena_run_v1 import main

    rc = main(
        [
            "--governance-json",
            str(attack),
            "--ecc-out",
            str(ecc_out),
            "--no-default-integrity-path",
            "--audit-jsonl",
            str(tmp_path / "audit.jsonl"),
            "--target",
            "BINANCE_API_KEY",
            "--",
            sys.executable,
            str(_REPO / "scripts" / "trade_dummy.py"),
        ]
    )
    assert rc == 1
    assert not ecc_out.exists()
    audit_txt = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip()
    row = json.loads(audit_txt.splitlines()[-1])
    assert row.get("kind") == "ABORTED_SECRET_STORE_MISS"


def test_hold_with_target_does_not_call_resolve(monkeypatch, tmp_path):
    fixture = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"
    ecc_out = tmp_path / "ecc.json"

    def _boom(_name: str):
        raise AssertionError("DPAPI must not be queried under HOLD")

    monkeypatch.setattr("scripts.athena_run_v1._resolve_secret", _boom)

    from scripts.athena_run_v1 import main

    rc = main(
        [
            "--governance-json",
            str(fixture),
            "--ecc-out",
            str(ecc_out),
            "--no-audit-append",
            "--target",
            "BINANCE_API_KEY",
            "--",
            sys.executable,
            str(_REPO / "scripts" / "trade_dummy.py"),
        ]
    )
    assert rc == 2


def test_audit_jsonl_records_denied_with_sha256(tmp_path):
    fixture = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"
    ecc_out = tmp_path / "ecc.json"
    audit_path = tmp_path / "audit.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "athena_run_v1.py"),
            "--governance-json",
            str(fixture),
            "--ecc-out",
            str(ecc_out),
            "--audit-jsonl",
            str(audit_path),
            "--",
            sys.executable,
            str(_REPO / "scripts" / "trade_dummy.py"),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    row = json.loads(lines[-1])
    assert row["schema"] == "athena_ecc_audit_row_v1"
    assert len(row["ecc_payload_sha256"]) == 64
    assert row["ecc"]["status"] == "DENIED"


def test_audit_webhook_posts_summary_when_url_set(monkeypatch, tmp_path):
    fixture = _REPO / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"
    ecc_out = tmp_path / "ecc.json"
    audit_path = tmp_path / "audit.jsonl"
    posted: list[bytes] = []

    class _Resp:
        def read(self, n: int = -1) -> bytes:
            return b"ok"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(req, timeout=None):
        posted.append(req.data)
        return _Resp()

    monkeypatch.setenv("ATHENA_ECC_AUDIT_WEBHOOK_URL", "https://example.invalid/ecc-hook")
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    from scripts.athena_run_v1 import main

    rc = main(
        [
            "--governance-json",
            str(fixture),
            "--ecc-out",
            str(ecc_out),
            "--audit-jsonl",
            str(audit_path),
            "--",
            sys.executable,
            str(_REPO / "scripts" / "trade_dummy.py"),
        ]
    )
    assert rc == 2
    assert len(posted) == 1
    body = json.loads(posted[0].decode("utf-8"))
    assert body["schema"] == "athena_ecc_audit_webhook_v1"
    assert body["ecc_status"] == "DENIED"
    assert len(body["ecc_payload_sha256"]) == 64
