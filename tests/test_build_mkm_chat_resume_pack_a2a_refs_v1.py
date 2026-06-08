"""Resume pack tp03 machine block — JSON only, not human MD."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def test_load_a2a_chain_refs_from_pilot(tmp_path):
    from build_mkm_chat_resume_pack_v1 import _load_a2a_chain_refs

    pilot = {
        "schema": "a2a_tp03_chain_ref_pilot_v1",
        "artifacts_present": 1,
        "artifacts_missing": 0,
        "kpi_headline": {"reduction_percent_if_pointers_only": 95.0},
        "aggregate_pointer_vs_full": {"tokens_saved_sum": 1000, "reduction_percent": 95.0},
        "artifacts": [
            {
                "artifact_id": "trackc_ops_dashboard",
                "pointer_handoff": {
                    "artifact_id": "trackc_ops_dashboard",
                    "artifact_path": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
                    "sha256": "abc",
                    "chain_step": "build",
                    "handoff_mode": "pointer_plus_fingerprint",
                    "essence_line": "schema=x status=ok",
                },
            }
        ],
    }
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True)
    (art / "a2a_tp03_chain_ref_pilot_v1_latest.json").write_text(
        json.dumps(pilot), encoding="utf-8"
    )

    refs = _load_a2a_chain_refs(tmp_path)
    assert refs is not None
    assert refs["schema"] == "mkm_chat_resume_a2a_chain_refs_v1"
    assert refs["pointer_rows"][0]["artifact_id"] == "trackc_ops_dashboard"
    assert refs["reduction_percent_if_pointers_only"] == 95.0


def test_load_a2a_chain_refs_missing_pilot(tmp_path):
    from build_mkm_chat_resume_pack_v1 import _load_a2a_chain_refs

    assert _load_a2a_chain_refs(tmp_path) is None
