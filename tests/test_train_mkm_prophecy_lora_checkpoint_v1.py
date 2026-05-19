"""Checkpoint helper for Windows fallback LoRA trainer."""

from __future__ import annotations

from pathlib import Path

from scripts.train_mkm_prophecy_lora_windows_fallback_v1 import _latest_checkpoint_dir


def test_latest_checkpoint_dir_picks_highest_step(tmp_path: Path) -> None:
    (tmp_path / "checkpoint-3").mkdir()
    (tmp_path / "checkpoint-40").mkdir()
    (tmp_path / "checkpoint-12").mkdir()
    assert _latest_checkpoint_dir(tmp_path) == str(tmp_path / "checkpoint-40")


def test_latest_checkpoint_dir_none_when_empty(tmp_path: Path) -> None:
    assert _latest_checkpoint_dir(tmp_path) is None
