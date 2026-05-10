from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trackc_dashboard_includes_lens_music_governance_fields():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    p = ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    lm = (doc.get("trackc") or {}).get("lens_music_audition_governance") or {}
    assert "state" in lm
    assert "warn_ratio" in lm
    assert "warn_ratio_threshold" in lm
    pb = (doc.get("trackc") or {}).get("lens_music_prompt_brake") or {}
    assert "state" in pb
    assert "auto_brake_active_rate" in pb
    assert "trend_state" in pb
    assert "trend_top_trigger" in pb
    pp = (doc.get("trackc") or {}).get("lens_music_prompt_poc_metric") or {}
    assert "state" in pp
    assert "style_delta_rate" in pp
    assert "overlay_style_match_rate" in pp
    rb = (doc.get("trackc") or {}).get("lens_music_prompt_poc_runbook") or {}
    assert "state" in rb
    assert "recommendation_count" in rb
    wb = (doc.get("trackc") or {}).get("lens_music_prompt_poc_runbook_webhook") or {}
    assert "dispatch_status" in wb
    assert "watch_gate_passed" in wb
    wh = (doc.get("trackc") or {}).get("lens_music_prompt_runbook_webhook_health") or {}
    assert "state" in wh
    assert "samples_in_window" in wh
    assert "sent_rate" in wh
    assert "top_skip_reason" in wh
