# Keywords: append_stt_routing_audit_log_v1, summarize_stt_routing_audit_log_v1

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_append_validates_and_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "audit.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/append_stt_routing_audit_log_v1.py"),
            "--out",
            str(out),
            "--route",
            "local",
            "--audio-ms",
            "1200",
            "--session-id",
            "sess-test-1",
            "--pii-redaction",
            "redacted_full",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["route"] == "local"
    assert row["audio_duration_ms"] == 1200


def test_summarize_rollup_counts(tmp_path: Path) -> None:
    out = tmp_path / "audit.jsonl"
    summary = tmp_path / "sum.json"
    for route, ms, lat in [("local", 1000, None), ("vendor", 2000, 120), ("vendor", 500, 300)]:
        cmd = [
            sys.executable,
            str(ROOT / "scripts/append_stt_routing_audit_log_v1.py"),
            "--out",
            str(out),
            "--route",
            route,
            "--audio-ms",
            str(ms),
            "--pii-redaction",
            "redacted_full",
        ]
        if route == "vendor":
            cmd += ["--provider", "gcp_speech_v2", "--latency-ms", str(lat)]
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/summarize_stt_routing_audit_log_v1.py"),
            "--in",
            str(out),
            "--out",
            str(summary),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr
    doc = json.loads(summary.read_text(encoding="utf-8"))
    assert doc["rows_total"] == 3
    assert doc["route_counts"]["vendor"] == 2
    assert doc["route_counts"]["local"] == 1
    assert doc["vendor_latency_ms_p95"] is not None
