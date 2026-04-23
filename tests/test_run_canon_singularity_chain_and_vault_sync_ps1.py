from __future__ import annotations

import subprocess
from pathlib import Path


def test_run_canon_singularity_chain_and_vault_sync_ps1_dry_run():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_canon_singularity_chain_and_vault_sync.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-DryRun",
        "-SkipVaultSync",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "build_original_corpus_regime_singularity_report_v1.py --canon-only" in out
    assert "enforce_canon_singularity_gate_health_v1.py --health-summary-json" in out
    assert "--max-fail-count 0" in out

