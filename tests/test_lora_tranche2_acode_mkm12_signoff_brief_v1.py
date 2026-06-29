from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_acode_mkm12_signoff_brief_v1() -> None:
    out = ROOT / "reports" / "tmp_acode_mkm12_signoff_brief_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lora_tranche2_acode_mkm12_signoff_brief_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_tranche2_acode_mkm12_signoff_brief_v1"
    assert doc["go_flags"]["multi_pack_production_go"] is False
    assert doc["lanes"]["bench_4x40_forced_alias_forbidden"] is True


def test_qwen12pack_acode_locked_eval_expanded_wrapper_help() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lora_tranche2_qwen12pack_acode_locked_eval_expanded_v1.py"),
            "--help",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
