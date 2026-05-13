"""Integration: build_logos_insight_bundle_v1 assembles valid logos_insight_bundle_v1 JSON."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LOGOS_INSIGHT_ND_FIXTURE_ROOT = (
    ROOT / "docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream"
)


def _non_degraded_upstream_paths() -> dict[str, Path]:
    r = LOGOS_INSIGHT_ND_FIXTURE_ROOT
    return {
        "morph": r / "morphology_registry.json",
        "sem": r / "semantic_edge_quality.json",
        "insight": r / "insight_candidates.json",
        "bridge": r / "bridge_edges.jsonl",
        "regime": r / "regime_shift.json",
    }


try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_cli_outputs_valid_schema(tmp_path: Path) -> None:
    paths = _non_degraded_upstream_paths()
    out = tmp_path / "bundle.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(paths["morph"]),
        "--semantic-quality-json",
        str(paths["sem"]),
        "--insight-candidates-json",
        str(paths["insight"]),
        "--bridge-edges-jsonl",
        str(paths["bridge"]),
        "--regime-shift-json",
        str(paths["regime"]),
        "--top-k",
        "4",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout

    bundle = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=bundle, schema=schema)

    assert bundle["degraded"] is False
    assert bundle["missing_upstream"] == []
    assert bundle["aggregation"]["morphology_summary"]["matched_hebrew_atoms"] == 80
    assert len(bundle["tension_hypotheses"]) >= 1
    axis_ids = {h.get("tension_axis_id") for h in bundle["tension_hypotheses"]}
    assert "semantic_overlap_below_half_with_bridge_v0" in axis_ids

    pack = bundle["citation_pack"]
    assert len(pack) == 3
    snippets = {p["snippet"] for p in pack}
    assert "foo bar" in snippets
    assert "snippet only no declared hash" in snippets
    assert "bridge span text" in snippets
    for p in pack:
        body = hashlib.sha256(p["snippet"].encode("utf-8")).hexdigest()
        assert p["quote_hash"] == f"sha256:{body}"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_all_missing_still_valid(tmp_path: Path) -> None:
    out = tmp_path / "empty_bundle.json"
    missing = tmp_path / "nope.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(missing),
        "--semantic-quality-json",
        str(missing),
        "--insight-candidates-json",
        str(missing),
        "--bridge-edges-jsonl",
        str(missing),
        "--regime-shift-json",
        str(missing),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    bundle = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=bundle, schema=schema)
    assert bundle["degraded"] is True
    assert len(bundle["missing_upstream"]) == 5
    assert bundle["aggregation"] == {}
    assert bundle["tension_hypotheses"] == []


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_citation_pack_limit(tmp_path: Path) -> None:
    paths = _non_degraded_upstream_paths()
    out = tmp_path / "bundle_limit.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(paths["morph"]),
        "--semantic-quality-json",
        str(paths["sem"]),
        "--insight-candidates-json",
        str(paths["insight"]),
        "--bridge-edges-jsonl",
        str(paths["bridge"]),
        "--regime-shift-json",
        str(paths["regime"]),
        "--citation-pack-limit",
        "1",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert len(bundle["citation_pack"]) == 1
    assert bundle["citation_pack"][0]["snippet"] == "foo bar"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_citation_pack_zero(tmp_path: Path) -> None:
    paths = _non_degraded_upstream_paths()
    out = tmp_path / "bundle_zero.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(paths["morph"]),
        "--semantic-quality-json",
        str(paths["sem"]),
        "--insight-candidates-json",
        str(paths["insight"]),
        "--bridge-edges-jsonl",
        str(paths["bridge"]),
        "--regime-shift-json",
        str(paths["regime"]),
        "--citation-pack-limit",
        "0",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["citation_pack"] == []
