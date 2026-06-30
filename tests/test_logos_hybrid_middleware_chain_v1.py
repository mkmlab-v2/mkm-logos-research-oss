"""Logos hybrid middleware chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "docs/final/artifacts/logos_verse_lexicon_join_sidecar_v2_corpus_full_latest.json"
CHAIN_OUT = ROOT / "reports/logos_hybrid_middleware_chain_v1_latest.json"
PY = sys.executable


@pytest.mark.skipif(not SIDECAR.is_file(), reason="31k sidecar missing")
def test_logos_hybrid_middleware_chain_exit_zero():
    proc = subprocess.run(
        [PY, "scripts/run_logos_hybrid_middleware_chain_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(CHAIN_OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_hybrid_middleware_chain_v1"
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["cloud_llm_called"] is False
    assert doc["steps"]["handoff_logos_context"]["ok"] is True
    assert doc["steps"]["umr_route"]["ok"] is True
    slot_v2 = doc["steps"]["umr_route"].get("domain_plugin_slot_v2") or {}
    assert slot_v2.get("slot_id") == "logos"
    assert slot_v2.get("knowledge_pin_floor") == 290_000
    assert doc["steps"]["hybrid_replay_stub"]["ok"] is True
    assert doc["b2c_commercial_surface"]["domain"] == "mkmlife.com"
    assert doc["b2c_commercial_surface"]["metering_enabled"] is False
