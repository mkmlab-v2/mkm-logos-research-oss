"""B-track Gemini must use AI Studio (vertexai=False), not Vertex OAuth."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_run_gemini_client_uses_vertexai_false() -> None:
    from scripts.generate_btrack_hypothesis_prophecy_v1 import _run_gemini

    bundle = {
        "schema": "btrack_llm_input_bundle_v1",
        "artifacts": {"macro_independent_lens": {"scores": {"direction_score": 0.1}}},
    }
    bundle_path = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
    if not bundle_path.is_file():
        pytest.skip("bundle missing")

    fake_resp = MagicMock()
    fake_resp.text = json.dumps(
        {
            "schema": "btrack_hypothesis_prophecy_v1",
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "ts_utc": "2026-05-17T00:00:00Z",
            "label": "[HYPO] test",
            "prediction": {
                "instrument": "btc",
                "horizon": "1d",
                "direction": "neutral",
                "confidence": 0.5,
            },
        }
    )
    captured: dict = {}

    def _fake_client(**kwargs):
        captured.update(kwargs)
        client = MagicMock()
        client.models.generate_content.return_value = fake_resp
        return client

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-studio-key"}, clear=False):
        with patch("google.genai.Client", side_effect=_fake_client):
            with patch("google.genai.types", MagicMock()):
                _run_gemini(bundle_path, model="gemini-2.5-flash", timeout=30, bundle=bundle)

    assert captured.get("vertexai") is False
    assert captured.get("api_key") == "test-studio-key"
