#!/usr/bin/env python3
"""Alignment routing tests — offline, no whisper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_alignment_routing_lib_v1 import (  # noqa: E402
    BACKEND_FASTER_WHISPER,
    BACKEND_WHISPERX,
    MODE_AUTO,
    MODE_WHISPERX,
    alignment_routing_contract_v1,
    build_alignment_routing_table_v1,
    resolve_alignment_backend_v1,
)


def test_auto_routes_pansori_to_whisperx() -> None:
    row = resolve_alignment_backend_v1(case_id="web_pansori", mode=MODE_AUTO)
    assert row["backend"] == BACKEND_WHISPERX
    assert row["rule_id"] == "case_id_pansori"


def test_auto_routes_deeply_to_faster_whisper() -> None:
    row = resolve_alignment_backend_v1(case_id="web_deeply", mode=MODE_AUTO)
    assert row["backend"] == BACKEND_FASTER_WHISPER
    assert row["rule_id"] == "default"


def test_domain_hint_override_traditional_vocal() -> None:
    row = resolve_alignment_backend_v1(
        case_id="custom_shorts_v1",
        mode=MODE_AUTO,
        domain_hint="traditional_vocal",
    )
    assert row["backend"] == BACKEND_WHISPERX


def test_explicit_cli_whisperx_mode() -> None:
    row = resolve_alignment_backend_v1(case_id="web_deeply", mode=MODE_WHISPERX)
    assert row["backend"] == BACKEND_WHISPERX
    assert row["rule_id"] == "cli_whisperx"


def test_routing_table_three_cases() -> None:
    table = build_alignment_routing_table_v1(
        ["web_pansori", "web_deeply", "web_youtube_edu"],
        mode=MODE_AUTO,
    )
    by_id = {r["case_id"]: r["backend"] for r in table}
    assert by_id["web_pansori"] == BACKEND_WHISPERX
    assert by_id["web_deeply"] == BACKEND_FASTER_WHISPER
    assert by_id["web_youtube_edu"] == BACKEND_FASTER_WHISPER


def test_alignment_routing_contract_schema() -> None:
    doc = alignment_routing_contract_v1()
    assert doc["schema"] == "ko_shorts_alignment_routing_v1"
    assert doc["send_gate"] == "HOLD"


def test_decision_includes_alignment_routing() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_ko_shorts_segment_backend_decision_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads((ROOT / "reports/ko_shorts_segment_backend_decision_v1_latest.json").read_text(encoding="utf-8"))
    assert "alignment_routing" in doc
    assert doc["alignment_routing"]["schema"] == "ko_shorts_alignment_routing_v1"
