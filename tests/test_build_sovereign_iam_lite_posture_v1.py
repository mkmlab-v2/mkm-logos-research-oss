"""build_sovereign_iam_lite_posture_v1 — B-track [HYPO] control-plane posture contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_sovereign_iam_lite_posture_v1 import build_posture_report  # noqa: E402

REGISTRY = ROOT / "docs/final/artifacts/sovereign_iam_lite_accounts_registry_v1_example.json"
POLICY = ROOT / "docs/final/artifacts/sovereign_iam_lite_policy_v1_draft.json"


def test_build_posture_mock_registry_critical_cap() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    report = build_posture_report(registry=registry, policy=policy)

    assert report["schema"] == "sovereign_iam_lite_posture_v1"
    assert report["research_only"] is True
    assert report["hypothesis_tag"] == "[HYPO]"
    assert report["send_gate"] == "HOLD"
    assert report["ready_for_external_send"] is False
    assert report["data_plane_excluded"] is True
    assert report["disclaimer_ko"]
    assert report["total_accounts_scanned"] == 20
    assert report["critical_breach_detected"] is True
    assert report["posture_score"] <= 35
    assert report["drift_count"] >= 4


def test_main_writes_report_json(tmp_path: Path) -> None:
    out = tmp_path / "posture.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_sovereign_iam_lite_posture_v1.py"),
            "--report-out",
            str(out),
            "--artifact-out",
            str(tmp_path / "artifact.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "sovereign_iam_lite_posture_v1"
    assert "reproduce" in data
