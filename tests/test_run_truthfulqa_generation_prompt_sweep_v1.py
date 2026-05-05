from __future__ import annotations

from pathlib import Path


def test_generation_prompt_sweep_script_exists() -> None:
    p = Path("scripts/run_truthfulqa_generation_prompt_sweep_v1.py")
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "truthfulqa_generation_prompt_sweep_v1" in text
    assert "--generation-system-prompt" in text or "generation_system_prompt" in text
