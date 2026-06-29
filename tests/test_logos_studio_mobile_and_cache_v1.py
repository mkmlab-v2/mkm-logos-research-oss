"""Logos Studio embedding sidecar + Capacitor shell hypo tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_capacitor_config_matches_artifact():
    artifact = json.loads(
        (ROOT / "docs/final/artifacts/logos_research_mobile_shell_hypo_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    cap = json.loads(
        (ROOT / "projects/no1kmedi/logos-research-native-hypo-v1/capacitor.config.json").read_text(
            encoding="utf-8"
        )
    )
    expected_url = f"{artifact['server_url'].rstrip('/')}{artifact['start_path']}"
    assert cap["appId"] == artifact["app_id"]
    assert cap["server"]["url"] == expected_url


def test_sidecar_script_exists():
    p = ROOT / "scripts/logos_studio_embedding_sidecar_v1.py"
    assert p.is_file()


def test_capacitor_verify_exit0():
    proc = subprocess.run(
        [sys.executable, "scripts/check_logos_research_capacitor_shell_hypo_v1.py"],
        cwd=ROOT,
    )
    assert proc.returncode == 0
