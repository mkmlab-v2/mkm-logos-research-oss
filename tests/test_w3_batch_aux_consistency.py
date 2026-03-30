from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_w3_batch_result_v1_to_v4_aux_non_gating_consistency() -> None:
    for idx in (1, 2, 3, 4):
        path = ART / f"W3_RESONANCE_BATCH_RESULT_V{idx}.json"
        doc = _load(path)

        rm = doc.get("run_meta") or {}
        assert rm.get("compute_status") == "executed_deterministic"
        assert rm.get("aux_adapter_version") == "w3_aux_adapter_v1"

        top = doc.get("top_n_results") or []
        assert top, f"top_n_results empty: V{idx}"
        for row in top:
            aux = row.get("aux_non_gating")
            assert isinstance(aux, dict), f"missing aux_non_gating in top_n_results: V{idx}"

        trace = doc.get("scoring_trace") or []
        assert trace, f"scoring_trace empty: V{idx}"
        for row in trace:
            comps = row.get("score_components") or {}
            aux = comps.get("aux_non_gating")
            assert isinstance(aux, dict), f"missing aux_non_gating in scoring_trace: V{idx}"
