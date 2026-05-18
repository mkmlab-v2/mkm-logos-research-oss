"""Contract: Run-FinanceMacroB2bCompressionEval_v1.ps1 references eval scripts and artifact paths (no full eval)."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Run-FinanceMacroB2bCompressionEval_v1.ps1"


def test_run_finance_macro_b2b_compression_eval_v1_ps1_paths() -> None:
    assert PS1.is_file()
    text = PS1.read_text(encoding="utf-8")
    assert "build_finance_macro_b2b_compression_eval_input_v1.py" in text
    assert "report_multilens_performance_eval.py" in text
    assert "finance_macro_b2b_compression_eval_input_v1.json" in text
    assert "finance_macro_b2b_compression_active_report_v1.json" in text
    assert "--mode" in text and "experimental" in text
    assert "--strategy" in text and "C" in text
    assert "--intensity" in text and "high" in text
    assert "SkipBuildEvalInput" in text
    assert "DryRun" in text
    assert '$ErrorActionPreference = "Stop"' in text


def test_run_finance_macro_b2b_compression_eval_v1_ps1_dry_run() -> None:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PS1),
        "-DryRun",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = cp.stdout
    assert "build_finance_macro_b2b_compression_eval_input_v1.py" in out
    assert "report_multilens_performance_eval.py" in out
    assert "finance_macro_b2b_compression_eval_input_v1.json" in out
    assert "finance_macro_b2b_compression_active_report_v1.json" in out
    assert "--mode experimental" in out
