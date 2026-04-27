import json
import subprocess
from pathlib import Path


def test_unified_self_critique_builds_from_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "unified_state_snapshot_v1.json"
    critique = tmp_path / "unified_self_critique_v1.json"

    build_snapshot = subprocess.run(
        ["py", "scripts/build_unified_state_snapshot_v1.py", "--out", str(snapshot)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_snapshot.returncode == 0, build_snapshot.stderr or build_snapshot.stdout

    build_critique = subprocess.run(
        ["py", "scripts/build_unified_self_critique_v1.py", "--snapshot", str(snapshot), "--out", str(critique)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_critique.returncode == 0, build_critique.stderr or build_critique.stdout

    payload = json.loads(critique.read_text(encoding="utf-8-sig"))
    assert payload["schema"] == "unified_self_critique_v1"
    assert payload["mode"] == "advisory_only"
    assert payload["auto_apply"] is False
    assert payload["assessment"]["decision"] in {"HOLD_STAGE", "MAINTAIN_CURRENT_STAGE"}
    assert isinstance(payload["counterfactual_review"]["best_alternative"], str)
