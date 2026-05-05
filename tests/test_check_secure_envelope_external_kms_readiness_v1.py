from __future__ import annotations

import os
import subprocess
import sys


def test_readiness_script_fails_without_required_env():
    env = os.environ.copy()
    env.pop("MKM_ENVELOPE_KEY_PROVIDER", None)
    cp = subprocess.run(
        [sys.executable, "scripts/check_secure_envelope_external_kms_readiness_v1.py"],
        cwd=".",
        env=env,
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "overall_ok" in cp.stdout


def test_readiness_script_passes_minimum_env_contract():
    env = os.environ.copy()
    env["MKM_ENVELOPE_KEY_PROVIDER"] = "external_kms"
    env["MKM_ENVELOPE_EXTERNAL_KEY_FILE"] = "dummy.json"
    env["MKM_ENVELOPE_A_TRACK_KEY_ID"] = "kms/a-track/test"
    env["MKM_ENVELOPE_B_TRACK_KEY_ID"] = "kms/b-track/test"
    cp = subprocess.run(
        [sys.executable, "scripts/check_secure_envelope_external_kms_readiness_v1.py"],
        cwd=".",
        env=env,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    assert '"overall_ok": true' in cp.stdout
