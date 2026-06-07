from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_family_anchor_son_kangmin_lived_fact_check_v1.py"
SESSION = ROOT / "docs/final/artifacts/family_anchor_fact_check_session_son_kangmin_v1_latest.json"
ANCHOR = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_son_kangmin_v1_latest.json"


def test_apply_kangmin_son_fact_check_merges_labs(tmp_path: Path) -> None:
    anchor_copy = tmp_path / "anchor.json"
    session_copy = tmp_path / "session.json"
    guide_copy = tmp_path / "guide.json"
    report = tmp_path / "report.json"

    anchor_copy.write_text(ANCHOR.read_text(encoding="utf-8"), encoding="utf-8")
    session_copy.write_text(SESSION.read_text(encoding="utf-8"), encoding="utf-8")
    guide_src = ROOT / "docs/final/artifacts/kangmin_son_integrated_guide_v1_latest.json"
    guide_copy.write_text(guide_src.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-json",
            str(session_copy),
            "--anchor-json",
            str(anchor_copy),
            "--guide-json",
            str(guide_copy),
            "--report-json",
            str(report),
        ],
        cwd=ROOT,
        check=True,
    )

    anchor = json.loads(anchor_copy.read_text(encoding="utf-8"))
    assert anchor["version"] == "1.1.0"
    assert anchor["clinical_labs_l0"]["anthropometrics"]["height_cm"] == 143
    assert anchor["clinical_labs_l0"]["labs_numeric_available"] is False
    assert anchor["clinical_labs_l0"]["labs"]["igf_1"]["value"] is None

    growth = next(x for x in anchor["supplementary_axes"] if x["axis"] == "growth_height")
    assert growth["responses"]["height_cm_confirmed"] == "143"
    assert growth["responses"]["lived_check_status"] == "completed"

    guide = json.loads(guide_copy.read_text(encoding="utf-8"))
    assert guide.get("clinical_labs_l0") is not None
    assert report.is_file()
