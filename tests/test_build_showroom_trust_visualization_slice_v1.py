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
