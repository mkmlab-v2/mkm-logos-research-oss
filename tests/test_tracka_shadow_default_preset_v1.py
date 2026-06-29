"""Track A shadow default preset — smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_tracka_shadow_default_preset_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, "scripts/build_tracka_shadow_default_preset_v1.py", "--skip-perf"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = ROOT / "reports/tracka_shadow_default_preset_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "tracka_shadow_default_preset_v1"
    assert int(doc.get("selected_terms_count") or 0) > 0
    assert doc.get("non_gating") is True
    assert (doc.get("track_wall") or {}).get("track_a_bridge") is False
    weights = ROOT / "reports/tracka_logic_weights_shadow_preset_v1_latest.json"
    assert weights.is_file()
    wdoc = json.loads(weights.read_text(encoding="utf-8-sig"))
    assert len(wdoc.get("weighted_terms") or []) == doc.get("selected_terms_count")
