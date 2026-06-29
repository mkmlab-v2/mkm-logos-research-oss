"""PersonaDiary lattice convergence v1 — schema, bloom slice, shatter caps."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/personadiary_lattice_convergence_session_v1.schema.json"
BLOOM = (
    ROOT / "projects/no1kmedi/public/data/personadiary_lattice_convergence_bloom_slice_v1.json"
)
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/personadiary_lattice_convergence_session_v1.example.json"


def _shatter_py(question: str, max_n: int = 24) -> list[str]:
    q = question.strip()
    if not q:
        return []
    out: list[str] = []
    chunks = [c for c in re.split(r"[\s,?.!;:·…、，。！？]+", q) if c]
    for chunk in chunks:
        if len(out) >= max_n:
            break
        if len(chunk) <= 4:
            out.append(chunk)
        else:
            out.append(chunk[:4])
            if len(out) < max_n and len(chunk) > 4:
                out.append(chunk[-2:])
    return out[:max_n]


def test_session_schema_phases_and_caps() -> None:
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    phases = doc["properties"]["phase"]["enum"]
    assert "shatter" in phases
    assert "vortex" in phases
    assert "converge" in phases
    assert doc["properties"]["shatter_tokens"]["maxItems"] == 24
    assert doc["properties"]["matched_hub_ids"]["maxItems"] == 5
    assert doc["properties"]["preview_only"]["const"] is True
    assert doc["properties"]["session_storage_only"]["const"] is True


def test_bloom_slice_magic_orb_contract() -> None:
    doc = json.loads(BLOOM.read_text(encoding="utf-8"))
    assert doc["schema"] == "magic_orb_graph_bloom_v1"
    assert doc.get("research_only") is True
    assert doc.get("non_gating") is True
    nodes = doc["nodes"]
    assert len(nodes) <= 64
    assert any(n["kind"] == "query" for n in nodes)
    for n in nodes:
        assert "id" in n and "label" in n and "kind" in n
        blob = json.dumps(n, ensure_ascii=False)
        assert "Track A" not in blob
        assert "압축률" not in blob
    assert doc.get("disclaimer_ko", "").startswith("[가설]")


def test_shatter_token_cap() -> None:
    long_q = " ".join(["마음"] * 40)
    tokens = _shatter_py(long_q)
    assert len(tokens) <= 24
    assert tokens


def test_example_session_fixture_if_present() -> None:
    if not EXAMPLE.exists():
        return
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert doc["schema"] == "personadiary_lattice_convergence_session_v1"
    assert doc["phase"] in {
        "idle",
        "shatter",
        "vortex",
        "breath",
        "ready",
        "converge",
        "encapsulate",
        "done",
    }
