from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_external_onepager_build_and_contract():
    root = Path.cwd()
    script = root / "scripts" / "build_mkm_trackc_external_onepager_v1.py"
    out = root / "docs" / "final" / "artifacts" / "mkm_trackc_external_onepager_latest.json"

    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "mkm_trackc_external_onepager_v1"
    cp = doc.get("channel_policy", {})
    assert cp.get("audience") == "external"
    assert cp.get("shadow_pnl_disclosure") == "DISABLED"
    assert "shadow_pnl" not in doc
