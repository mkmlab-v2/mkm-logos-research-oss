"""PersonaDiary moment polish — runtime Azure direct; batch Ollama optional."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import polish_personadiary_moment_copy_v1 as polish  # noqa: E402


def test_runtime_explicit_off_skips_chain() -> None:
    with patch.object(polish, "_runtime_polish_flag", return_value="off"):
        assert polish.runtime_polish_enabled() is False
    with patch.object(polish, "runtime_polish_enabled", return_value=False):
        out, meta = polish.polish_summary_with_fallback(
            "점심 추천: 국밥",
            intent="meal",
            query="점심?",
            mode="runtime",
        )
    assert out is None
    assert meta.get("reason") == "runtime_disabled"


def test_runtime_auto_no_azure_skips_chain() -> None:
    with patch.object(polish, "_runtime_polish_flag", return_value="auto"):
        with patch.object(polish, "_azure_env_ok", return_value=False):
            assert polish.runtime_backends_available() is False
            assert polish.runtime_polish_enabled() is False


def test_runtime_azure_direct_skips_ollama() -> None:
    with patch.object(polish, "runtime_polish_enabled", return_value=True):
        with patch.object(polish, "azure_polish_enabled", return_value=True):
            with patch.object(polish, "ollama_polish_summary") as ollama_mock:
                with patch.object(
                    polish,
                    "azure_polish_summary",
                    return_value=("따뜻한 한 그릇으로 가볍게.", {"applied": True, "deployment": "gpt-4o-mini"}),
                ):
                    out, meta = polish.polish_summary_with_fallback(
                        "점심 추천: 국밥",
                        intent="meal",
                        query="점심?",
                        mode="runtime",
                    )
    ollama_mock.assert_not_called()
    assert out == "따뜻한 한 그릇으로 가볍게."
    assert meta.get("backend") == "azure_openai"
    assert meta.get("applied") is True
    assert len(meta.get("attempts") or []) == 1


def test_batch_ollama_success_skips_azure() -> None:
    with patch.object(polish, "polish_enabled", return_value=True):
        with patch.object(
            polish,
            "ollama_polish_summary",
            return_value=("오늘은 가볍게.", {"applied": True, "model": "gemma4:e2b"}),
        ):
            with patch.object(polish, "azure_polish_summary") as azure_mock:
                out, meta = polish.polish_summary_with_fallback(
                    "점심 추천: 국밥",
                    intent="meal",
                    query="점심?",
                    mode="batch",
                )
    azure_mock.assert_not_called()
    assert out == "오늘은 가볍게."
    assert meta.get("backend") == "ollama"


def test_azure_env_incomplete_returns_reason() -> None:
    with patch.object(polish, "_azure_env_ok", return_value=False):
        out, meta = polish.azure_polish_summary("요약", intent="meal", query="q")
    assert out is None
    assert meta.get("reason") == "azure_env_incomplete"
