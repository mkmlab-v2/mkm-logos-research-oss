"""Logos question 4D shadow — path coherence scoring + gate [HYPO][NON_GATING]."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADOW = ROOT / "scripts/logos_question_4d_shadow_v1.py"
GATE = ROOT / "scripts/check_logos_question_4d_coherence_gate_v1.py"


def _load_shadow():
    spec = importlib.util.spec_from_file_location("logos_question_4d_shadow_v1", SHADOW)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_path_coherence_high_for_adjacent_verses():
    mod = _load_shadow()
    idx = {
        "Ps.89.28": {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5},
        "Ps.89.29": {"S": 0.51, "L": 0.49, "K": 0.5, "M": 0.5},
    }
    path = {
        "path_id": "p_adj",
        "steps": ["verse:Ps.89.28", "verse:Ps.89.29"],
        "match_score": 5,
    }
    shadow = mod.score_path_four_d_coherence(path, idx)
    assert shadow["four_d_coherence"] is not None
    assert float(shadow["four_d_coherence"]) >= 0.95


def test_enrich_router_reranks_by_composite_rank():
    mod = _load_shadow()
    idx = {
        "Ps.89.28": {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5},
        "Ps.89.29": {"S": 0.51, "L": 0.49, "K": 0.5, "M": 0.5},
        "Jer.31.33": {"S": 0.1, "L": 0.9, "K": 0.1, "M": 0.9},
        "Jer.31.34": {"S": 0.9, "L": 0.1, "K": 0.9, "M": 0.1},
    }
    router = {
        "query": "test",
        "paths": [
            {
                "path_id": "low_coh",
                "match_score": 5,
                "steps": ["verse:Jer.31.33", "verse:Jer.31.34"],
            },
            {
                "path_id": "high_coh",
                "match_score": 5,
                "steps": ["verse:Ps.89.28", "verse:Ps.89.29"],
            },
        ],
    }
    enriched = mod.enrich_router_with_4d_shadow(router, verse_index=idx, rerank=True)
    assert enriched["paths"][0]["path_id"] == "high_coh"
    assert enriched["four_d_shadow_v1"]["schema"] == "logos_question_4d_shadow_v1"


def test_coherence_gate_script_smoke(tmp_path: Path):
    mod = _load_shadow()
    router = {
        "paths": [
            {
                "path_id": "p1",
                "match_score": 5,
                "steps": ["verse:Ps.89.28", "verse:Ps.89.29"],
            }
        ]
    }
    idx = {
        "Ps.89.28": {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5},
        "Ps.89.29": {"S": 0.51, "L": 0.49, "K": 0.5, "M": 0.5},
    }
    enriched = mod.enrich_router_with_4d_shadow(router, verse_index=idx)
    router_path = tmp_path / "router.json"
    router_path.write_text(json.dumps(enriched, ensure_ascii=False), encoding="utf-8")
    gate_out = tmp_path / "gate.json"
    r = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--router-json",
            str(router_path),
            "--min-mean",
            "0.5",
            "--out",
            str(gate_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    gate = json.loads(gate_out.read_text(encoding="utf-8"))
    assert gate.get("ok") is True


def test_insight_payload_embeds_4d_shadow_when_router_has_it():
    builder = ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"
    spec = importlib.util.spec_from_file_location("build_magic_orb_question_insight_payload_v1", builder)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    shadow_mod = _load_shadow()
    router = {
        "bridges_matched": 1,
        "paths": [
            {
                "path_id": "p1",
                "bridge_artifact": "x.json",
                "steps": ["verse:Ps.89.28", "verse:Ps.89.29"],
                "match_score": 5,
                "note_ko": "test",
            }
        ],
        "verse_ids": [],
    }
    idx = {
        "Ps.89.28": {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5},
        "Ps.89.29": {"S": 0.51, "L": 0.49, "K": 0.5, "M": 0.5},
    }
    router = shadow_mod.enrich_router_with_4d_shadow(router, verse_index=idx)
    bundle = {"schema": "semantic_rag_bridge_insight_bundle_v1", "rag_evidence": []}
    payload = mod.build_payload(
        query="test query",
        query_id="q_test",
        bundle=bundle,
        chain=None,
        router=router,
        graph_bloom=None,
    )
    assert payload.get("logos_4d_shadow_v1", {}).get("schema") == "logos_question_4d_shadow_v1"
    assert payload["calibration_reference"].get("mean_path_coherence") is not None
    assert "4d_shadow" in (payload["structured_insight_slots"][1]["text"])
