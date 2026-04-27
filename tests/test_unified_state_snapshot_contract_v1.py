import json
import subprocess
from pathlib import Path


def test_unified_snapshot_build_and_validate(tmp_path: Path) -> None:
    out = tmp_path / "unified_state_snapshot_v1.json"

    build = subprocess.run(
        [
            "py",
            "scripts/build_unified_state_snapshot_v1.py",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr or build.stdout
    assert out.is_file()

    payload = json.loads(out.read_text(encoding="utf-8-sig"))
    assert payload["schema"] == "unified_state_snapshot_v1"
    assert payload["schema_version"] == 1
    assert isinstance(payload["state_nodes"], dict)
    assert isinstance(payload["summary"], dict)

    validate = subprocess.run(
        [
            "py",
            "scripts/validate_unified_state_snapshot_v1.py",
            "--input",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr or validate.stdout
