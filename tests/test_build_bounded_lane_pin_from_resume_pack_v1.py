"""Build bounded lane pin from resume pack v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_bounded_lane_pin_from_resume_pack_v1.py"
RUNNER = ROOT / "scripts/run_bounded_lane_loop_v1.py"
PIN_SCHEMA = ROOT / "docs/final/schemas/bounded_lane_pin_v1.schema.json"


def _run_builder(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_build_infra_pin_validates() -> None:
    proc = _run_builder(["--lane", "infra", "--dry-run"])
    assert proc.returncode == 0, proc.stderr
    pin = json.loads(proc.stdout)
    assert pin["schema"] == "bounded_lane_pin_v1"
    assert pin["lane"] == "infra"
    assert pin["next_action_one_line"]
    assert len(pin["next_action_one_line"]) <= 240
    assert pin["steps"][0]["argv"] == [
        "scripts/build_mkm_chat_resume_pack_v1.py",
        "--lane",
        "infra",
    ]


def test_extract_next_action_from_mission_log() -> None:
    if not (ROOT / "MISSION_LOG.md").is_file():
        return
    sys.path.insert(0, str(ROOT))
    from scripts.build_bounded_lane_pin_from_resume_pack_v1 import (
        extract_next_action_one_line,
    )

    for lane in ("infra", "ms", "oracle", "design"):
        action = extract_next_action_one_line(ROOT, lane)
        assert action
        assert "6/" in action or "다음" in action or "bounded loop" in action.lower()


def test_build_write_and_loop_dry_run_infra() -> None:
    out = ROOT / "reports/_bounded_lane_pin_infra_test_latest.json"
    proc = _run_builder(["--lane", "infra", "--out", str(out)])
    assert proc.returncode == 0, proc.stderr
    pin = json.loads(out.read_text(encoding="utf-8"))
    assert pin["lane"] == "infra"
    try:
        loop = subprocess.run(
            [sys.executable, str(RUNNER), "--pin", str(out), "--dry-run"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert loop.returncode == 0, loop.stderr
        summary = json.loads(
            (ROOT / "reports/bounded_lane_loop_v1_latest.json").read_text(encoding="utf-8")
        )
        assert summary["outcome_class"] == "shadow_pass"
        assert summary["lane"] == "infra"
    finally:
        out.unlink(missing_ok=True)


def test_design_lane_resume_pack_without_lane_flag() -> None:
    proc = _run_builder(["--lane", "design", "--dry-run"])
    assert proc.returncode == 0, proc.stderr
    pin = json.loads(proc.stdout)
    assert pin["lane"] == "design"
    assert pin["steps"][0]["argv"] == ["scripts/build_mkm_chat_resume_pack_v1.py"]
    assert "peer_handoff_pointer" not in pin


def test_infra_pin_includes_peer_handoff_when_brief_exists() -> None:
    brief = (
        ROOT
        / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_infra_v1_latest.md"
    )
    if not brief.is_file():
        return
    proc = _run_builder(["--lane", "infra", "--dry-run"])
    assert proc.returncode == 0, proc.stderr
    pin = json.loads(proc.stdout)
    assert pin.get("peer_handoff_pointer") == brief.relative_to(ROOT).as_posix()


def test_lane_fixtures_validate_against_schema() -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(PIN_SCHEMA.read_text(encoding="utf-8"))
    fixture_dir = ROOT / "docs/final/artifacts/fixtures"
    for lane in ("ms", "oracle", "infra", "design"):
        path = fixture_dir / f"bounded_lane_pin_{lane}_v1.example.json"
        if not path.is_file():
            proc = _run_builder(["--write-fixtures"])
            assert proc.returncode == 0, proc.stderr
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)
        assert doc["lane"] == lane
