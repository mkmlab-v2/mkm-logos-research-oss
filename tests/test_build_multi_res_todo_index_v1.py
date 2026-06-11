"""Regression: multi_res_todo_index_v1 build + schema ([HYPO])."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from multi_res_todo_index_lib_v1 import (  # noqa: E402
    build_todo_index_document,
    parse_central_checkpoints,
    parse_mission_log_lane_actions,
)

SCHEMA = ROOT / "docs/final/schemas/multi_res_todo_index_v1.schema.json"

SAMPLE_MISSION = """\
### 🧭 Cursor IDE · 3층 To-Do

**post-340 다음 1타:** build_multi_res_todo_index_v1.py → reports/multi_res_todo_index_v1_latest.json

### ⚙️ 차세대 엔진

**레인 다음 1타:** WATCH noop 고정
"""

SAMPLE_CENTRAL = """\
<!-- ATHENA_CHECKPOINT_V1_START -->
- **2026-06-10T00:00:00Z** — test checkpoint one
- **2026-06-09T12:00:00Z** — test checkpoint two
<!-- ATHENA_CHECKPOINT_V1_END -->
"""


def test_parse_mission_log_lane_actions() -> None:
    rows = parse_mission_log_lane_actions(SAMPLE_MISSION)
    assert len(rows) >= 2
    assert any("build_multi_res_todo_index" in r["essence"] for r in rows)
    assert rows[0]["priority"] == 10


def test_parse_central_checkpoints() -> None:
    rows = parse_central_checkpoints(SAMPLE_CENTRAL)
    assert len(rows) == 2
    assert rows[0]["timestamp_utc"] == "2026-06-10T00:00:00Z"


def test_build_document_shape(tmp_path: Path) -> None:
    (tmp_path / "MISSION_LOG.md").write_text(SAMPLE_MISSION, encoding="utf-8")
    central = tmp_path / "docs/final/CENTRAL_AGENT_MEMORY_V1.md"
    central.parent.mkdir(parents=True)
    central.write_text(SAMPLE_CENTRAL, encoding="utf-8")

    doc = build_todo_index_document(tmp_path, generated_at_utc="2026-06-10T00:00:00Z")
    assert doc["schema"] == "multi_res_todo_index_v1"
    assert doc["research_only"] is True
    assert doc["todo_queue_auto_enqueue"] is False
    assert doc["meta"]["n_low_res"] >= 2
    assert len(doc["coordinate_map"]) >= 1


def test_schema_validates_built_doc(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    (tmp_path / "MISSION_LOG.md").write_text(SAMPLE_MISSION, encoding="utf-8")
    doc = build_todo_index_document(tmp_path, generated_at_utc="2026-06-10T00:00:00Z")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_build_script_writes_output() -> None:
    import subprocess

    if not (ROOT / "MISSION_LOG.md").is_file():
        pytest.skip("MISSION_LOG.md local-only SSOT")

    proc = subprocess.run(
        [sys.executable, "scripts/build_multi_res_todo_index_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "reports/multi_res_todo_index_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "multi_res_todo_index_v1"
    assert doc["meta"]["n_low_res"] >= 5
