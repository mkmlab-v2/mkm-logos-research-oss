"""ingest_saving_the_news_public_event_local_v1.prepare_payload"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "ingest_saving_the_news_public_event_local_v1",
        ROOT / "scripts/ingest_saving_the_news_public_event_local_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_prepare_payload_adds_character_id() -> None:
    mod = _load()
    out = mod.prepare_payload({"event_id": "x", "source": "t"}, event_id_suffix="1")
    assert out["active_character_id"] == "dog_sentinel"
    assert out["event_id"] == "x-1"
