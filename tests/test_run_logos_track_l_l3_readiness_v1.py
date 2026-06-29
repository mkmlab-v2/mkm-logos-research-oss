"""Track L L3 GraphRAG bridge readiness smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_logos_track_l_l3_readiness_v1.py"


def test_run_logos_track_l_l3_readiness_v1_dry(monkeypatch) -> None:
    from scripts import run_logos_track_l_l3_readiness_v1 as mod

    def fake_run_py(args, *, timeout=300):
        if "run_logos_track_l_l2" in args[0]:
            return 0, '{"ok": true}'
        if "run_logos_subgraph_graphrag_router" in args[0]:
            out = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
            out.write_text(
                json.dumps(
                    {
                        "schema": "logos_subgraph_graphrag_router_v1",
                        "bridges_matched": 2,
                        "non_gating": True,
                        "query": "q01",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return 0, ""
        if args[0:2] == ["-m", "pytest"]:
            return 0, ""
        return 1, "unexpected"

    monkeypatch.setattr(mod, "_run_py", fake_run_py)
    for rel in (
        "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md",
        "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
        "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
        "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json",
        "docs/final/schemas/logos_subgraph_graphrag_router_v1.schema.json",
    ):
        p = ROOT / rel
        if not p.is_file() and rel.endswith(".json"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}", encoding="utf-8")
        elif not p.is_file() and rel.endswith(".md"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# bridge\n", encoding="utf-8")

    out = ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json"
    rc = mod.main(["--output-json", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_track_l_l3_readiness_v1"
    assert doc["l3_ok"] is True


def test_run_logos_track_l_l3_readiness_v1_script_exists() -> None:
    assert RUNNER.is_file()


def test_build_logos_s1_shadow_packet_includes_track_l_advisory() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_s1_shadow_promotion_review_packet_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json").read_text(
            encoding="utf-8"
        )
    )
    track_l = doc.get("track_l_advisory") or {}
    assert track_l.get("label") == "Track L"
    assert track_l.get("non_gating") is True
