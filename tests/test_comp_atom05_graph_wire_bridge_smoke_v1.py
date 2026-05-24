# @MKM12-METADATA
# Type: Logic
# Purpose: COMP-ATOM-05 evaluate_report wire selective bridge smoke.

from __future__ import annotations

from scripts.mkm_graph_wire_bridge_influence_v1 import build_case_graph_wire_influence_map
from scripts.report_multilens_performance_eval import evaluate_report


def test_graph_wire_selective_bridge_changes_jaccard_on_graph_case() -> None:
    raw = (
        "State 3 to 11 dominates in bootstrap data but this is read only "
        "and cannot trigger babel empire transition policy"
    )
    doc = {
        "compression_cases": [
            {
                "id": "gw1",
                "domain": "general",
                "raw_text": raw,
                "compressed_text": raw,
                "reconstructed_text": raw,
            }
        ],
        "fusion_answer_cases": [],
    }
    routes = [
        {
            "case_id": "gw1",
            "expanded_node_count": 12,
            "anchor_terms": ["babel", "exodus", "empire"],
        }
    ]
    influence = build_case_graph_wire_influence_map(routes)
    assert influence["gw1"]["bridge_boost"] is True

    base_kw = dict(
        source_input="fixture.json",
        mode="experimental",
        strategy="A",
        intensity="extreme",
        use_domain_router=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        general_max_saving_rate=0.35,
        sensitive_max_saving_rate=0.3,
        hangul_max_saving_rate=0.6,
    )
    off = evaluate_report(
        doc,
        apply_gematria_4d_bridge_policy=False,
        graph_wire_selective_bridge=False,
        emit_semantic_pointer=True,
        **base_kw,
    )
    on = evaluate_report(
        doc,
        apply_gematria_4d_bridge_policy=False,
        graph_wire_selective_bridge=True,
        case_graph_wire_influence=influence,
        emit_semantic_pointer=True,
        **base_kw,
    )
    row_off = off["compression_metrics"]["cases"][0]
    row_on = on["compression_metrics"]["cases"][0]
    sp = row_on.get("semantic_pointer") or {}
    assert sp.get("graph_wire_influence_v1", {}).get("bridge_boost") is True
    assert row_on.get("gematria_4d_bridge_policy_applied") is True
    assert row_off.get("gematria_4d_bridge_policy_applied") is False
