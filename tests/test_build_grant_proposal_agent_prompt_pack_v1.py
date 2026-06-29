from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_grant_proposal_agent_prompt_pack_v1 import build_pack, load_route, load_tasks_index

ROOT = Path(__file__).resolve().parent.parent
ROUTE = ROOT / "reports/opendata_327_grant_model_route_v1_latest.json"
TASKS = ROOT / "data/grant_proposal/opendata_327_draft_tasks_v1.jsonl"
BUILDER = ROOT / "scripts/build_grant_proposal_agent_prompt_pack_v1.py"


@pytest.mark.skipif(not ROUTE.is_file(), reason="route artifact missing")
def test_pack_counts_eight_llm_nine_script() -> None:
    pack = build_pack(load_route(ROUTE), load_tasks_index(TASKS))
    assert pack["counts"]["llm_draft"] == 8
    assert pack["counts"]["script_gate"] == 9
    assert pack["counts"]["human_only"] == 12
    assert len(pack["llm_draft_tasks"]) == 8
    for t in pack["llm_draft_tasks"]:
        assert "cursor_user_prompt" in t
        assert "FORBIDDEN" in t["cursor_user_prompt"]


@pytest.mark.skipif(not ROUTE.is_file(), reason="route artifact missing")
def test_builder_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "pack.json"
    out_md = tmp_path / "pack.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--route-json",
            str(ROUTE),
            "--tasks-jsonl",
            str(TASKS),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["schema"] == "opendata_327_grant_agent_prompt_pack_v1"
    assert out_md.read_text(encoding="utf-8").startswith("# OpenData 327")
