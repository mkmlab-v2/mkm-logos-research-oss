# Keywords: build_showroom_trust_visualization_slice_v1

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_slice_from_dashboard(tmp_path: Path) -> None:
    dash = tmp_path / "dash.json"
    out = tmp_path / "slice.json"
    dash.write_text(
        json.dumps(
            {
                "trackc": {
                    "trust_visualization_v0": {
                        "state": "OK",
                        "role": "trust_visualization_read_only_v0",
                        "final_action": "WATCH",
                        "logos_non_gating": True,
                    },
                    "stt_routing_audit_log_slice": {
                        "state": "OK",
                        "role": "silver_stt_audit_summary_v0",
                        "rows_total": 2,
                        "vendor_share_by_event_pct": 50.0,
                    },
                    "patient_intake_fusion_b_track": {
                        "state": "OK",
                        "clinical_sasang_label": "소음인",
                        "cross_checks_v1": {
                            "myeongni_sasang_clinical_v1": {
                                "status": "match",
                                "status_ko": "일치(표면)",
                                "constitution_id": "soeum_in",
                            }
                        },
                        "deep_link_count": 5,
                        "boming_term_count": 12,
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_showroom_trust_visualization_slice_v1.py"),
            "--dashboard",
            str(dash),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "showroom_trust_visualization_slice_v0"
    assert doc.get("hypothesis_tag") == "[HYPO]"
    assert doc["trust_visualization_v0"].get("final_action") == "WATCH"
    assert doc["stt_routing_audit_log_slice"].get("vendor_share_by_event_pct") == 50.0
    assert "compression_governance_v0" in doc
    assert doc["compression_governance_v0"].get("role") == "compression_governance_read_only_v0"
    assert doc["compression_board_ms_v0"].get("role") == "compression_board_ms_research_read_only_v0"
    pit = doc.get("patient_intake_b_track_v0") or {}
    assert pit.get("state") == "OK"
    assert pit.get("auto_prescription_forbidden") is True
    assert pit.get("clinical_sasang_label") == "소음인"


def test_build_slice_missing_dashboard_writes_nodata(tmp_path: Path) -> None:
    out = tmp_path / "slice2.json"
    missing = tmp_path / "nope.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_showroom_trust_visualization_slice_v1.py"),
            "--dashboard",
            str(missing),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["trust_visualization_v0"].get("state") == "NODATA"
    assert doc["stt_routing_audit_log_slice"].get("state") == "NODATA"
    # Compression slice reads frozen KPI/policy artifacts, not the dashboard path.
    assert doc["compression_governance_v0"].get("role") == "compression_governance_read_only_v0"
    assert doc["compression_board_ms_v0"].get("role") == "compression_board_ms_research_read_only_v0"
