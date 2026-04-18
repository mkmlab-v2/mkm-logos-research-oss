from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_sidecar_lens_hit_agreement_v1_latest.json"


def test_lens_hit_agreement_artifact() -> None:
    assert ART.is_file(), "run: py scripts/eval_btrack_insight_sidecar_lens_hit_agreement_v1.py"
    data = json.loads(ART.read_text(encoding="utf-8-sig"))
    assert data.get("schema") == "btrack_insight_sidecar_lens_hit_agreement_v1"
    assert data.get("version") == "1.2.0"
    assert data.get("research_only") is True
    by = data.get("by_lens")
    assert isinstance(by, dict)
    for k in ("logos", "myeongni", "sasang"):
        assert k in by
        blk = by[k]
        assert "rows_used" in blk and "rate_agree_with_actual" in blk
        assert "skipped_no_sidecar_row" in blk

    bi = data.get("by_instrument")
    assert isinstance(bi, dict)
    for ins in ("all", "kospi", "btc"):
        assert ins in bi
        assert "logos" in bi[ins]

    bda = data.get("by_dated_aux")
    assert isinstance(bda, dict)
    for k in ("myeongni_16_state_jsonl", "sasang_dynamics_jsonl"):
        assert k in bda
        for ins in ("all", "kospi", "btc"):
            blk = bda[k][ins]
            assert "rows_used" in blk and "rate_agree_with_actual" in blk
