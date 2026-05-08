from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "promote_logos_to_shadow_live_v1.py"


def test_promote_logos_to_shadow_live_enforces_non_gating(tmp_path: Path):
    out = tmp_path / "shadow_status.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--reason",
            "pytest regression guard",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out.is_file()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_shadow_promotion_status_v1"

    checks = doc.get("checks") or {}
    assert checks.get("auto_trade_enable_false") is True

    track_wall = doc.get("track_wall") or {}
    assert track_wall.get("promotion_to_a_track_allowed") is False
    assert track_wall.get("live_trigger_auto_enabled") is False
    assert track_wall.get("requires_human_review_each_release") is True

