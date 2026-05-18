"""Lens combo backtest enriches per-eval_date maps from calendar JSONL."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prophecy_lens_combo_backtest_v1 import (
    _enrich_lens_maps_from_jsonl,
    _extract_lens_maps,
)


def test_enrich_lens_maps_from_jsonl_fills_eval_date(tmp_path: Path) -> None:
    sasang = tmp_path / "sasang.jsonl"
    myeongni = tmp_path / "myeongni.jsonl"
    sasang.write_text(
        json.dumps(
            {
                "ts_utc": "2026-04-10T12:00:00+00:00",
                "mapping_target": "bear",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    myeongni.write_text(
        json.dumps(
            {
                "ts_utc": "2026-04-10T13:00:00Z",
                "mapping_target": "bear",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = [{"eval_date": "2026-04-15", "instrument": "btc"}]
    my_map: dict[str, int] = {}
    sa_map: dict[str, int] = {}
    _enrich_lens_maps_from_jsonl(
        rows=rows,
        myeongni_map=my_map,
        sasang_map=sa_map,
        myeongni_jsonl=myeongni,
        sasang_jsonl=sasang,
    )
    assert my_map["2026-04-15"] == -1
    assert sa_map["2026-04-15"] == -1


def test_extract_lens_maps_empty_sidecar() -> None:
    my, sa, lg = _extract_lens_maps({})
    assert my == {}
    assert sa == {}
    assert lg == 0
