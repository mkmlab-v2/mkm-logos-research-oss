"""Evolution sovereignty spine — delta recorder and SSOT refresh gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extract_snapshot_from_minimal_report() -> None:
    from scripts.build_evolution_sovereignty_delta_v1 import extract_snapshot

    report = {
        "schema": "lens_sovereignty_report_v1_2",
        "generated_at_utc": "2026-06-12T20:44:21Z",
        "promotion_ready": False,
        "role_contract_verdict": "ROLE_PARTIAL",
        "supplementary_verdict": "SUPP_ALIGNED",
        "supplementary_passes": ["sasang", "myeongni", "logos"],
        "role_verdict_lines": ["role contract passes (1/3): ['sasang']"],
        "daily_kospi_wf": {
            "verdict": "KEEP",
            "best_lens": {
                "arm_id": "lens3_4ai_overlay",
                "soft_hit_rate_wf": 0.5082,
            },
        },
    }
    snap = extract_snapshot(report)
    assert snap["daily_wf_verdict"] == "KEEP"
    assert snap["role_contract_verdict"] == "ROLE_PARTIAL"
    assert snap["supplementary_verdict"] == "SUPP_ALIGNED"
    assert snap["best_lens_arm_id"] == "lens3_4ai_overlay"
    assert snap["role_pass_count"] == 1
    assert snap["supplementary_pass_count"] == 3


def test_build_delta_detects_verdict_change(tmp_path: Path) -> None:
    from scripts.build_evolution_sovereignty_delta_v1 import build_delta

    report = tmp_path / "report.json"
    snapshot = tmp_path / "snap.json"
    history = tmp_path / "hist.jsonl"
    queue = tmp_path / "queue.json"
    out = tmp_path / "delta.json"

    base = {
        "schema": "lens_sovereignty_report_v1_2",
        "generated_at_utc": "2026-06-12T20:44:21Z",
        "promotion_ready": False,
        "role_contract_verdict": "ROLE_PARTIAL",
        "supplementary_verdict": "SUPP_ALIGNED",
        "supplementary_passes": ["sasang"],
        "role_verdict_lines": ["role contract passes (1/3): ['sasang']"],
        "daily_kospi_wf": {"verdict": "KEEP", "best_lens": {"arm_id": "a", "soft_hit_rate_wf": 0.5}},
    }
    report.write_text(json.dumps(base), encoding="utf-8")
    doc1 = build_delta(
        report_path=report,
        snapshot_path=snapshot,
        history_path=history,
        queue_path=queue,
        out_path=out,
    )
    assert doc1["first_run"] is True
    assert doc1["delta_detected"] is False

    base["role_contract_verdict"] = "ROLE_ALIGNED"
    base["role_verdict_lines"] = ["role contract passes (2/3): ['sasang', 'logos']"]
    report.write_text(json.dumps(base), encoding="utf-8")
    doc2 = build_delta(
        report_path=report,
        snapshot_path=snapshot,
        history_path=history,
        queue_path=queue,
        out_path=out,
    )
    assert doc2["delta_detected"] is True
    assert "role_contract_verdict" in doc2["changes"]
    assert history.read_text(encoding="utf-8").strip()


def test_refresh_skips_when_fingerprint_unchanged(tmp_path: Path, monkeypatch) -> None:
    from scripts import refresh_lens_sovereignty_ssot_if_delta_v1 as mod

    ssot = tmp_path / "a.json"
    ssot.write_text("{}", encoding="utf-8")
    st = ssot.stat()
    monkeypatch.setattr(mod, "_ssot_input_paths", lambda r: (ssot,))
    fp = mod._input_fingerprint(tmp_path)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"last_fingerprint": fp}), encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")
    out = tmp_path / "out.json"

    monkeypatch.setattr(mod, "_ssot_input_paths", lambda r: (ssot,))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "refresh",
            "--workspace-root",
            str(tmp_path),
            "--state",
            str(state),
            "--report",
            str(report),
            "--out-json",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["skipped"] is True


def test_evolution_lightweight_loop_writes_v2_schema() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_evolution_lightweight_loop_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = ROOT / "docs/final/artifacts/evolution_lightweight_loop_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "evolution_lightweight_loop_v2"
    assert doc["spine"]["sovereignty_ssot_refresh_always"] is True
    assert len(doc["spine"]["steps"]) >= 2
