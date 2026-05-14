"""build_showroom_topology_radar_snapshot_v1.py CLI (emit + optional jsonschema)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_showroom_topology_radar_snapshot_v1.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_strict_empty_workspace_exits_2(tmp_path: Path) -> None:
    r = _run("--workspace-root", str(tmp_path), "--out", "snap/out.json")
    assert r.returncode == 2


def test_allow_stub_empty_workspace_writes_valid_json(tmp_path: Path) -> None:
    r = _run(
        "--workspace-root",
        str(tmp_path),
        "--out",
        "snap/out.json",
        "--allow-stub-ref",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = tmp_path / "snap" / "out.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "showroom_topology_radar_snapshot_v1"
    assert data["no_trade_signals"] is True
    assert data["artifact_refs"] == ["docs/final/schemas/showroom_topology_radar_snapshot_v1.example.json"]


def test_collects_existing_candidate_paths(tmp_path: Path) -> None:
    rel = Path("docs/final/artifacts/logos_track_c_freshness_sidecar_v1_latest.json")
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}", encoding="utf-8")
    r = _run("--workspace-root", str(tmp_path), "--out", "radar/snap.json")
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads((tmp_path / "radar" / "snap.json").read_text(encoding="utf-8"))
    assert any("freshness_sidecar" in ref for ref in data["artifact_refs"])


@pytest.mark.skipif(
    not (ROOT / "docs/final/schemas/showroom_topology_radar_snapshot_v1.schema.json").is_file(),
    reason="schema missing",
)
def test_repo_workspace_emit_validates_against_schema() -> None:
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:
        pytest.skip("jsonschema not installed")

    out_rel = "reports/showroom_topology_radar_snapshot_emit_pytest_tmp.json"
    snap_path = ROOT / out_rel.replace("/", os.sep)
    try:
        r = _run(
            "--workspace-root",
            str(ROOT),
            "--out",
            out_rel,
            "--allow-stub-ref",
        )
        assert r.returncode == 0, r.stderr + r.stdout
        data = json.loads(snap_path.read_text(encoding="utf-8"))
        schema = json.loads(
            (ROOT / "docs/final/schemas/showroom_topology_radar_snapshot_v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.validate(instance=data, schema=schema)
    finally:
        if snap_path.is_file():
            snap_path.unlink()
