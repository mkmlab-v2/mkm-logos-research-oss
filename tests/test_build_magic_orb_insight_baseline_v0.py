"""magic_orb insight baseline v0 — offline helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts/build_magic_orb_insight_baseline_v0.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("baseline_v0", BASELINE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_measure_live_sends_user_agent() -> None:
    mod = _load_module()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"source":"static","payload":{"rag_evidence":[],"graph_bloom":{"stats":{}}}}'
    ctx = MagicMock()
    ctx.__enter__.return_value = mock_resp
    ctx.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=ctx) as urlopen:
        out = mod._measure_live("위기 가운데 언약의 안정과 신실")
    assert out.get("ok") is True
    req = urlopen.call_args[0][0]
    assert req.get_header("User-agent") == mod.LIVE_PROBE_UA
