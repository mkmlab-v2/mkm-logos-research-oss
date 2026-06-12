"""MKM Family identity federation — policy and schema smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_policy_human_approval_db_merge_false() -> None:
    policy = json.loads(
        (ROOT / "docs/final/artifacts/mkm_family_identity_policy_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["human_approval"]["personadiary_mkmlife_db_merge"] is False
    assert policy["human_approval"]["cross_product_identity_federation"] is True


def test_account_schema_required_fields() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/mkm_family_account_v1.schema.json").read_text(encoding="utf-8")
    )
    required = set(schema["required"])
    assert "mkm_account_id" in required
    assert "auth_providers" in required


def test_check_mkm_family_identity_gate_paths_exist() -> None:
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_mkm_family_identity_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
