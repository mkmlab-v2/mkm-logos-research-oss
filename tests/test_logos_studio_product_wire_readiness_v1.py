from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_logos_studio_product_wire_readiness_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_studio_product_wire_readiness_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = ROOT / "docs/final/artifacts/logos_studio_product_wire_readiness_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_studio_product_wire_readiness_v1"
    assert ((doc.get("public_facing_contract") or {}).get("tag")) == "[NON_GATING]"
