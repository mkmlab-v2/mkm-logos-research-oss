"""Harness v2 birth PoC + dual-pass envelope helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dual_pass_envelope_helpers_import_and_contract() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import (
        build_harness_v2_format_wrap_instruction,
        build_harness_v2_insight_only_instruction,
        dual_pass_deterministic_format_v1,
        normalize_hypo_tag_prefix,
    )

    assert normalize_hypo_tag_prefix("[HYPOTHESIS] x").startswith("[HYPO]")
    msg = build_harness_v2_insight_only_instruction(
        deterministic_payload={"full_saju": {"saju": {"year": "갑자"}}},
        lang="ko",
        sha256_hex="a" * 64,
    )
    assert "myeongri_ai_interpretation_envelope_v1" not in msg
    wrap = build_harness_v2_format_wrap_instruction(
        deterministic_payload={"full_saju": {"saju": {"year": "갑자"}}},
        lang="ko",
        sha256_hex="b" * 64,
        pass1_insight="[HYPO] 테스트",
    )
    assert "[HYPO] 테스트" in wrap
    assert callable(dual_pass_deterministic_format_v1)


def test_birth_poc_cli_smoke(tmp_path: Path) -> None:
    out = tmp_path / "birth.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_myeongri_harness_v2_birth_poc_v1.py"),
            "--utc-instant",
            "1992-03-12T17:00:00Z",
            "--iana-tz",
            "Asia/Seoul",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["envelope_contract_ok"] is True
    assert doc["interpretation_envelope"]["hypothesis_tier"] == "B"
