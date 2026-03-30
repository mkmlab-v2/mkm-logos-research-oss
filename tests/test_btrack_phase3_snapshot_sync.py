# @MKM12-METADATA
# Type: Logic
# Purpose: Ensure Phase3 snapshot JSON fence stays in sync with SSOT.
# Keywords: cross-ref, snapshot, sync, fence

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SSOT = _ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
_SNAP = _ROOT / "docs" / "final" / "btrack_phase3_cross_ref_snapshot.md"


def _first_json_fence(text: str) -> str:
    lines = text.splitlines()
    open_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "```json":
            open_idx = i
            break
    assert open_idx is not None, "snapshot markdown must contain a ```json fence"
    for j in range(open_idx + 1, len(lines)):
        if lines[j].strip() == "```":
            return "\n".join(lines[open_idx + 1 : j]) + "\n"
    raise AssertionError("snapshot markdown has unclosed ```json fence")


def test_btrack_phase3_snapshot_json_fence_matches_ssot() -> None:
    assert _SSOT.is_file(), f"missing SSOT file: {_SSOT}"
    assert _SNAP.is_file(), f"missing snapshot file: {_SNAP}"
    ssot_doc = json.loads(_SSOT.read_text(encoding="utf-8"))
    fence_doc = json.loads(_first_json_fence(_SNAP.read_text(encoding="utf-8")))
    assert fence_doc == ssot_doc, (
        "snapshot JSON fence drifted from SSOT. "
        "Run: py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply"
    )
