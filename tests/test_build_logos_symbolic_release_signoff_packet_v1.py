from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_symbolic_release_signoff_packet_v1.py"


def test_build_release_signoff_packet_smoke(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "decision": "GO_RESEARCH_PROMOTION_CANDIDATE_WITH_HUMAN_APPROVAL",
                "metrics_snapshot": {"hit_rate": 0.9},
                "track_wall": {"promotion_to_a_track_allowed": False, "live_trigger_auto_enabled": False},
            }
        ),
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"status": "APPROVED_CANDIDATE"}), encoding="utf-8")
    reval = tmp_path / "reval.json"
    reval.write_text(json.dumps({"status": "ok", "overall": {"hit_rate": 0.9}}), encoding="utf-8")
    hygiene = tmp_path / "hygiene.json"
    hygiene.write_text(json.dumps({"status": "ok", "news_counts": {"non_synthetic_rows": 20}}), encoding="utf-8")
    breakdown = tmp_path / "breakdown.json"
    breakdown.write_text(json.dumps({"summary": {"n_sources": 3}}), encoding="utf-8")
    out_json = tmp_path / "packet.json"
    out_md = tmp_path / "packet.md"

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-json",
            str(gate),
            "--candidate-json",
            str(candidate),
            "--revalidation-json",
            str(reval),
            "--hygiene-json",
            str(hygiene),
            "--source-breakdown-json",
            str(breakdown),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("summary", {}).get("recommended_manual_gate") == "GO_MANUAL_A_TRACK_GATE"
    assert doc.get("summary", {}).get("all_checks_pass") is True
    assert out_md.is_file()

