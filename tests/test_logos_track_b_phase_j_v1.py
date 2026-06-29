from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
MS_PACK = _ROOT / "reports/external_validation_ms_evidence_pack_v1_latest"


def test_logos_ms_bundle() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    manifest = json.loads((MS_PACK / "manifest.json").read_text(encoding="utf-8"))
    bundle = manifest.get("track_b_logos_bundle") or {}
    assert len(bundle.get("files") or []) >= 4
    assert (MS_PACK / "logos_track_b").is_dir()
    assert (MS_PACK / "ms_track_b_logos_internal_pointer_v1.txt").is_file()


def test_phase_j_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_j_v1.py"),
            "--skip-phase-i",
            "--skip-ms-pack-rebuild",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    phase_j = json.loads((_ROOT / "reports/logos_track_b_phase_j_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_j.get("ok") is True
    assert phase_j.get("ms_pack_bundle_ok") is True
