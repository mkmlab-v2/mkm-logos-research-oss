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
    hs = (doc.get("trackc") or {}).get("lens_music_hormone_state") or {}
    assert "state" in hs
    assert "stress_index_0_1" in hs
    assert "recovery_buffer_0_1" in hs
    assert "inertia_index_0_1" in hs
    assert "gematria_trace_present" in hs
    assert "gematria_applied_ema_alpha_multiplier" in hs
    ht = (doc.get("trackc") or {}).get("lens_music_hormone_trend") or {}
    assert "state" in ht
    assert "high_stress_rate" in ht
    assert "max_consecutive_high_stress" in ht
    assert "operator_hint" in ht
    assert "mean_rag_metabolism_bounded_drift_0_1" in ht
    assert "rows_with_rag_drift" in ht
    htw = (doc.get("trackc") or {}).get("lens_music_hormone_trend_webhook") or {}
    assert "dispatch_status" in htw
    assert "dispatch_only_on_watch" in htw
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
    tail = (doc.get("trackc") or {}).get("governance_agent_decisions_tail") or {}
    assert tail.get("source_rel") == "reports/agent_decisions_log.jsonl"
    assert "path_exists" in tail
    assert "tail_line_budget" in tail
    assert "entries" in tail
    assert isinstance(tail.get("entries"), list)
    ck = doc.get("commercial_kpi_pointers") or {}
    assert ck.get("role") == "pointer_only"
    assert "boundary_note" in ck
    assert "ssot" in ck
    assert "ssot_present" in ck
    assert "artifact_present" in ck
    assert "snapshots" in ck
    assert isinstance((ck.get("snapshots") or {}).get("track_a_metering_weekly"), dict)
    lmg = (doc.get("trackc") or {}).get("lens_music_promotion_gate") or {}
    assert "promotion_process_pass" in lmg
    assert "promotion_process_exit_code" in lmg
    assert "promotion_gate_m31_profile" in lmg
