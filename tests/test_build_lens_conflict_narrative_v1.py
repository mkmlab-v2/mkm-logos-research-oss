"""Lens conflict narrative builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_lens_conflict_narrative_v1 import build_lens_conflict_narrative  # noqa: E402


def test_conflict_narrative_has_telegram_line(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "myeongni_independent_lens_latest.json").write_text(
        json.dumps({"scores": {"direction_score": 0.0}}), encoding="utf-8"
    )
    (art / "logos_independent_lens_latest.json").write_text(
        json.dumps({"scores": {"direction_score": -0.2}}), encoding="utf-8"
    )
    (art / "sasang_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "scores": {"direction_score": 0.1},
                "sasang_stream_outputs": {"machine_readables": {"heat_proxy": 0.7}},
            }
        ),
        encoding="utf-8",
    )
    doc = build_lens_conflict_narrative(tmp_path)
    assert doc.get("telegram_one_liner_ko")
    assert "NON_GATING" in doc["telegram_one_liner_ko"]
