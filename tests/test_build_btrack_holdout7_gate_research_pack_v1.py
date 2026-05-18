"""Holdout7 gate research pack."""
from __future__ import annotations

from pathlib import Path


def test_build_pack_smoke() -> None:
    from scripts.build_btrack_holdout7_gate_research_pack_v1 import build_pack, holdout_dates_from_cf

    holdout = holdout_dates_from_cf(
        Path(__file__).resolve().parents[1] / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
    )
    if len(holdout) != 7:
        return
    panel_path = Path(__file__).resolve().parents[1] / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
    if not panel_path.is_file():
        return
    import json

    from scripts.build_btrack_holdout7_gate_research_pack_v1 import CF, DUMP, PER_DATE, _load

    doc = build_pack(
        panel=_load(panel_path),
        cf=_load(CF),
        dump=_load(DUMP),
        per_doc=_load(PER_DATE),
        aux_grid=None,
        holdout_dates=holdout,
    )
    assert doc["schema"] == "btrack_holdout7_gate_research_pack_v1"
    assert doc["findings"]["advisory_holdout7_wrong_overlap_n"] == 3
    assert len(doc["findings"]["holdout7_uncovered_by_either_gate"]) == 4


def test_gate_pack_latest_if_present() -> None:
    p = Path(__file__).resolve().parents[1] / "reports" / "btrack_holdout7_gate_research_pack_v1_latest.json"
    if not p.is_file():
        return
    import json

    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["model_swap_poc_status"] == "closed_no_promote"
    assert doc["auto_promote"] is False
