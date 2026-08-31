"""Tests for MKM digestion engine (Mastication → Wiring → Fact-Lock)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MD = ROOT / "tests/fixtures/mkm_digestion_tier0_input_v1.md"
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_research_digested_fact_v1.schema.json"
BUILD = ROOT / "scripts/build_mkm_research_digested_facts_v1.py"
WIRE = ROOT / "scripts/map_digested_facts_to_mkm_plane_v1.py"
GATE = ROOT / "scripts/check_mkm_digested_facts_gate_v1.py"
CHAIN = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def test_build_parses_digested_facts_heading_with_parenthetical(tmp_path: Path) -> None:
    md = tmp_path / "tier0.md"
    md.write_text(
        "# Tier0\n\n## Digested facts (MKM active fact-lite targets)\n\n"
        "### fact_id: demo_arxiv_fact\n"
        "- metric_name: latency_reduction_pct\n"
        "- value: 13.81\n"
        "- unit: percent\n"
        "- comparison_arm: CE-CoLLM\n"
        "- verification_status: Unknown\n"
        "- arxiv_id: 2507.16731\n",
        encoding="utf-8",
    )
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts

    doc = build_mkm_research_digested_facts(source_path=md)
    by_id = {f["fact_id"]: f for f in doc["facts"]}
    assert "demo_arxiv_fact" in by_id
    assert by_id["demo_arxiv_fact"]["provenance"]["arxiv_id"] == "2507.16731"


def test_build_extracts_explicit_and_table_facts() -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    ids = {f["fact_id"] for f in doc["facts"]}
    assert "demo_b3_dual_plane_floor" in ids
    assert "demo_external_latency" in ids
    assert any(f["comparison_arm"] == "CE-CoLLM" for f in doc["facts"])
    assert doc["schema"] == "mkm_research_digested_fact_v1"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_fixture_validates_schema() -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts, validate_digested

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    validate_digested(doc)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_wiring_manifest_marks_explicit_wired(tmp_path: Path) -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts
    from scripts.map_digested_facts_to_mkm_plane_v1 import map_digested_facts_to_mkm_plane

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    wired = map_digested_facts_to_mkm_plane(doc)
    by_id = {e["fact_id"]: e for e in wired["wiring_manifest"]}
    assert by_id["demo_b3_dual_plane_floor"]["wired"] is True
    assert by_id["demo_b3_dual_plane_floor"]["wiring_status"] == "BINDING_CANDIDATE"
    assert by_id["demo_external_latency"]["wired"] is False
    assert by_id["demo_external_latency"]["wiring_status"] == "HOLD_NO_TARGET"


def test_gate_passes_right_wiring_against_baseline() -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts
    from scripts.check_mkm_digested_facts_gate_v1 import run_gate

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    result = run_gate(doc)
    assert result["ok"] is True
    entries = {e["fact_id"]: e for e in result["entries"]}
    assert entries["demo_b3_dual_plane_floor"]["gate_status"] == "pass"
    assert entries["demo_external_latency"]["gate_status"] == "skipped"


def test_value_in_text_percent() -> None:
    from scripts.check_digested_numeric_fact_v1 import value_in_text

    assert value_in_text(13.81, "latency reduced by 13.81% on average", "percent") is True
    assert value_in_text(99.9, "accuracy was 12.3 percent", "percent") is False


def test_active_fact_lite_offline_skips_promotion() -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts
    from scripts.check_digested_numeric_fact_v1 import run_active_fact_lite

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    updated, report = run_active_fact_lite(doc, offline=True)
    assert report["promoted_to_right"] == 0
    assert report.get("marked_wrong", 0) == 0
    assert all(
        (f.get("verification") or {}).get("status") in {"Right", "Unknown"}
        for f in updated["facts"]
    )


def test_active_fact_lite_online_marks_miss_as_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts
    from scripts.check_digested_numeric_fact_v1 import run_active_fact_lite

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    for fact in doc["facts"]:
        if fact["fact_id"] == "demo_external_latency":
            fact["provenance"]["arxiv_id"] = "2507.16731"

    def _fake_fetch(ids: list[str], **kwargs: object) -> dict[str, dict[str, str]]:
        return {
            "2507.16731": {
                "title": "Hybrid inference survey",
                "abstract": "Latency reduced by 13.81% in one configuration.",
            }
        }

    monkeypatch.setattr(
        "scripts.check_digested_numeric_fact_v1.fetch_arxiv_records_batch",
        _fake_fetch,
    )
    updated, report = run_active_fact_lite(doc, offline=False)
    by_id = {f["fact_id"]: f for f in updated["facts"]}
    assert by_id["demo_external_latency"]["verification"]["status"] == "Right"
    assert report["promoted_to_right"] >= 1


def test_digestion_chain_includes_active_fact_step(tmp_path: Path) -> None:
    digested = tmp_path / "fixture_digested_facts_latest.json"
    chain_report = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(FIXTURE_MD),
            "--digested-out",
            str(digested),
            "--out-json",
            str(chain_report),
            "--offline",
            "--skip-citation-lock",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    chain = json.loads(chain_report.read_text(encoding="utf-8"))
    assert chain["ok"] is True
    assert chain["steps"]["active_fact_lite"]["exit_code"] == 0


def test_digestion_chain_exit_0_on_fixture(tmp_path: Path) -> None:
    digested = tmp_path / "fixture_digested_facts_latest.json"
    chain_report = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--input",
            str(FIXTURE_MD),
            "--digested-out",
            str(digested),
            "--out-json",
            str(chain_report),
            "--offline",
            "--skip-citation-lock",
            "--skip-active-fact",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_cli_build_strict_exit_0(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--input", str(FIXTURE_MD), "--out", str(out), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"


def test_production_guard_forbids_escape_hatch_flag(tmp_path: Path) -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts

    digested = tmp_path / "digested.json"
    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    digested.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    active = ROOT / "scripts/check_digested_numeric_fact_v1.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(active),
            "--input",
            str(digested),
            "--report",
            str(tmp_path / "report.json"),
            "--production",
            "--no-mark-miss-as-wrong",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 3
    assert "forbidden" in proc.stdout


def test_production_flags_static_scan_exit_0() -> None:
    guard = ROOT / "scripts/check_mkm_digestion_production_flags_v1.py"
    proc = subprocess.run(
        [sys.executable, str(guard)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_compute_digested_digest_metrics_fixture() -> None:
    from scripts.build_mkm_research_digested_facts_v1 import build_mkm_research_digested_facts
    from scripts.compute_digested_digest_metrics_v1 import compute_digested_digest_metrics
    from scripts.map_digested_facts_to_mkm_plane_v1 import map_digested_facts_to_mkm_plane

    doc = build_mkm_research_digested_facts(source_path=FIXTURE_MD)
    doc = map_digested_facts_to_mkm_plane(doc)
    metrics = compute_digested_digest_metrics(doc)
    assert metrics["fact_count"] >= 3
    assert metrics["wired_count"] >= 1
    assert metrics["gate_pass_count"] >= 1
    assert 0.0 <= metrics["gate_pass_rate"] <= 1.0


def test_validate_dosage_passes_fixture_extract() -> None:
    from scripts.validate_dosage_v1 import run_validate_dosage

    extract_path = (
        ROOT / "docs/final/artifacts/herbs_formulas_lecture_dual_citation_v1_herbs_formulas_extract_latest.json"
    )
    if not extract_path.is_file():
        pytest.skip("fixture extract artifact missing")
    doc = json.loads(extract_path.read_text(encoding="utf-8"))
    report = run_validate_dosage(doc)
    assert report["ok"] is True
    assert report["dosage_hit_count"] == 0


def test_validate_dosage_fails_without_expert_review(tmp_path: Path) -> None:
    from scripts.validate_dosage_v1 import run_validate_dosage

    doc = {
        "schema": "herbs_formulas_extract_v1",
        "expert_review_required": False,
        "payload": {"clinical": {"dose_note": "桂枝 9g · 芍药 9g"}},
    }
    report = run_validate_dosage(doc)
    assert report["ok"] is False
    assert report["dosage_hit_count"] >= 1
