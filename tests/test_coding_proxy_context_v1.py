"""Unit tests: coding proxy structured block preserve."""
from __future__ import annotations

from scripts.core.coding_proxy_context_v1 import partition_coding_text
from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface
from scripts.run_cursor_coding_compress_bench_v1 import _load_lane_intensity, _selected_profile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CC005 = (
    "Task: add scripts/build_local_dev_backup_manifest_v1.py and run_cursor_coding_compress_bench_v1.py. "
    "Constraints: B-track research_only, no active report mutation, pytest smoke. "
    "Files: scripts/*.py, data/btrack/*.jsonl, reports/*_latest.json. "
    "Verify with py -m pytest -q. Do not create new .md unless user asks."
)


def test_partition_cc005() -> None:
    body, preserved = partition_coding_text(CC005)
    assert "Task:" in body
    assert len(preserved) == 3
    assert any("Constraints:" in p for p in preserved)
    assert any("Files:" in p for p in preserved)
    assert any("Verify with" in p for p in preserved)


def test_structured_preserve_extract_anchors() -> None:
    profile = _selected_profile()
    li = _load_lane_intensity(ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json")
    out = coding_proxy_compress_surface(CC005, profile, lane="long_multifile", lane_intensity=li)
    surface = out["surface"].lower()
    assert out.get("structured_preserve") is True
    assert "research_only" in surface
    assert "scripts/*.py" in surface
    assert "data/btrack/*.jsonl" in surface
    assert "py -m pytest -q" in surface
