"""Per-lens BTC+KOSPI bundle merge."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_prophecy_hit_rate_per_lens_bundle_v1 import (  # noqa: E402
    _resolve_kospi_score_path,
    build_per_lens_bundle,
)


def test_resolve_kospi_skips_empty_only(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    empty = art / "btrack_prophecy_score_kospi_only_latest.json"
    empty.write_text(json.dumps({"rows": []}), encoding="utf-8")
    dual = art / "btrack_prophecy_score_kospi_dual_v2_per_date_latest.json"
    dual.write_text(
        json.dumps({"rows": [{"instrument": "kospi", "actual_direction": "bull"}]}),
        encoding="utf-8",
    )
    picked = _resolve_kospi_score_path(art)
    assert picked is not None
    assert picked.name == dual.name


def test_bundle_merges_kospi_leg(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "btrack_prophecy_score_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_prophecy_score_kospi_dual_v2_per_date_latest.json").write_text(
        json.dumps({"rows": [{"instrument": "kospi"}]}),
        encoding="utf-8",
    )

    btc_doc = {
        "schema": "prophecy_hit_rate_per_lens_v1",
        "legs": {
            "btc": {
                "lenses": [{"lens_id": "myeongni", "price_directional_hit_rate": 0.6, "n_evaluated": 25}]
            }
        },
    }
    kospi_doc = {
        "schema": "prophecy_hit_rate_per_lens_v1",
        "legs": {
            "kospi": {
                "lenses": [{"lens_id": "myeongni", "price_directional_hit_rate": 0.55, "n_evaluated": 20}]
            }
        },
    }

    def fake_run(ws: Path, score_json: Path, out_path: Path) -> dict:
        doc = btc_doc if "kospi" not in score_json.name else kospi_doc
        out_path.write_text(json.dumps(doc), encoding="utf-8")
        return doc

    with patch(
        "build_prophecy_hit_rate_per_lens_bundle_v1._run_builder",
        side_effect=fake_run,
    ):
        merged = build_per_lens_bundle(tmp_path)

    assert "btc" in merged["legs"]
    assert "kospi" in merged["legs"]
    assert merged.get("sources", {}).get("kospi_score")
