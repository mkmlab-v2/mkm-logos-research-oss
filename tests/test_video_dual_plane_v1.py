from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_RIG = ROOT / "tests/fixtures/mkm_video_rig_walk_raw_stub_v1.json"
TL_SPEC = ROOT / "tests/fixtures/video_tl_spec_walk_stub_v1.json"
EXAMPLE_RIG = ROOT / "docs/final/schemas/mkm_video_rig_stub_v1.example.json"


def test_schema_example_validates():
    jsonschema = __import__("pytest").importorskip("jsonschema")
    schema = json.loads((ROOT / "docs/final/schemas/mkm_video_rig_stub_v1.schema.json").read_text(encoding="utf-8"))
    doc = json.loads(EXAMPLE_RIG.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_project_clips_oob_and_fov():
    from scripts.video_rig_dual_plane_v1_lib import project_video_rig

    rig = json.loads(RAW_RIG.read_text(encoding="utf-8"))
    out = project_video_rig(rig)
    actor = out["objects"][0]["bbox_3d_track"][1]
    assert actor["center"][0] <= 5.0
    assert actor["center"][2] >= 0.0
    assert out["camera"]["pose_track"][0]["fov"] <= 90.0
    assert len(out["projection_stage"]["clip_notes"]) >= 2


def test_dual_tl_gate_raw_gt_post_zero():
    from scripts.video_rig_dual_plane_v1_lib import evaluate_dual_plane_tl_gate

    rig = json.loads(RAW_RIG.read_text(encoding="utf-8"))
    tl = json.loads(TL_SPEC.read_text(encoding="utf-8"))
    report = evaluate_dual_plane_tl_gate(raw_rig=rig, tl_spec=tl)
    assert report["collapsed_combined_score"] is None
    assert report["raw"]["violation_rate"] > 0.0
    assert report["post_project"]["violation_rate"] == 0.0


def test_check_video_tl_gate_cli(tmp_path: Path):
    out = tmp_path / "gate.json"
    projected = tmp_path / "rig_projected.json"
    env = dict(**__import__("os").environ)
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{__import__('os').pathsep}{prev}"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_video_tl_gate_v1.py"),
            "--rig-json",
            str(RAW_RIG),
            "--tl-spec",
            str(TL_SPEC),
            "--out",
            str(out),
            "--export-projected-rig",
            str(projected),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "video_tl_gate_report_v1"
    assert projected.is_file()
