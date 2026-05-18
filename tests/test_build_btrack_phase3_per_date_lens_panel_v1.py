from __future__ import annotations

import json
from pathlib import Path

from scripts.build_btrack_phase3_per_date_lens_panel_v1 import build_panel_rows, main

ROOT = Path(__file__).resolve().parents[1]


def _load_lens_asof():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "btrack_phase3_lens_asof_v1",
        ROOT / "scripts" / "btrack_phase3_lens_asof_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_build_panel_rows_has_lens_block() -> None:
    lens_mod = _load_lens_asof()
    score_rows = [
        {
            "eval_date": "2026-04-02",
            "instrument": "btc",
            "predicted_direction": "bull",
            "actual_direction": "bear",
        }
    ]
    panel = build_panel_rows(
        score_rows,
        lens_mod=lens_mod,
        instrument="btc",
        sasang_jsonl=lens_mod.DEFAULT_SASANG_JSONL,
        myeongni_jsonl=lens_mod.DEFAULT_MYEONGNI_JSONL,
        logos_lens=lens_mod.DEFAULT_LOGOS_LENS,
    )
    assert len(panel) == 1
    assert "lens" in panel[0]
    assert panel[0]["lens"].get("logos_non_gating") is True
    assert "myeongni_sign" in panel[0]["lens"]


def test_main_writes_jsonl(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    score.write_text(
        json.dumps(
            {
                "schema": "btrack_prophecy_score_v1",
                "rows": [
                    {
                        "eval_date": "2026-04-02",
                        "instrument": "btc",
                        "predicted_direction": "neutral",
                        "actual_direction": "bull",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "panel.jsonl"
    meta = tmp_path / "panel.meta.json"
    rc = main(
        [
            "--score-json",
            str(score),
            "--out-jsonl",
            str(out),
            "--out-meta",
            str(meta),
        ]
    )
    assert rc == 0
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
