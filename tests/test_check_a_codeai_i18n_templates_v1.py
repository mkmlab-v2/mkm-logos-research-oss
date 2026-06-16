"""a-codeai template i18n (EN default + hreflang) smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_a_codeai_i18n_templates_strict() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/check_a_codeai_i18n_templates_v1.py", "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads((ROOT / "docs/final/artifacts/a_codeai_i18n_routes_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("all_ok") is True
    assert doc.get("policy", {}).get("default_locale") == "en"
