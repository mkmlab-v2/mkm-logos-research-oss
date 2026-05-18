from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_single_anchor_promotion_blockers_smoke(tmp_path: Path) -> None:
    go = {
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "track_a_auto_promotion": False,
        "single_anchor_operational": {
            "union_rows": 31102,
            "lexical_in_complete_jsonl": 31087,
            "gap_pipeline_stub_rows": 15,
            "mt_only_residual_taxonomy": "textual_variant_omission",
            "coverage_diff_complete_gap": 15,
            "regression_49_passed": True,
            "multi_orbit_b_track": {"merge_tr_into_complete_forbidden": True},
        },
        "lexical_decode_blocker": {"forbidden_external_claim": "perfect_canon_100_percent_lexical"},
    }
    shadow = {
        "track_wall": {
            "promotion_to_a_track_allowed": False,
            "live_trigger_auto_enabled": False,
        }
    }
    b2b = {"ready_for_internal_meeting": True, "ready_for_external_send": False}
    go_path = tmp_path / "go.json"
    shadow_path = tmp_path / "shadow.json"
    b2b_path = tmp_path / "b2b.json"
    out_path = tmp_path / "blockers.json"
    go_path.write_text(json.dumps(go), encoding="utf-8")
    shadow_path.write_text(json.dumps(shadow), encoding="utf-8")
    b2b_path.write_text(json.dumps(b2b), encoding="utf-8")

    script = ROOT / "scripts" / "build_logos_single_anchor_promotion_blockers_v1.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--go-no-go-json",
            str(go_path),
            "--shadow-status-json",
            str(shadow_path),
            "--b2b-readiness-json",
            str(b2b_path),
            "--output",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_single_anchor_promotion_blockers_v1"
    assert doc["promotion_tiers_blocked"]["track_a_live_trading"] is True
    assert len(doc["blockers"]) >= 5
