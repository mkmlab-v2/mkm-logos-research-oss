# -*- coding: utf-8 -*-
"""Integrated Wellness Solution v2 — schema, resolver, minor 소음인 guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "final" / "schemas" / "integrated_wellness_solution_v2.schema.json"
SEED = (
    ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "fixtures"
    / "integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json"
)
LEXICON = ROOT / "docs" / "final" / "artifacts" / "a_code_wellness_archetype_lexicon_v1.json"
CORE = ROOT / "scripts" / "integrated_wellness_solution_v2_core.py"


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_seed_validates_against_schema() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    seed = json.loads(SEED.read_text(encoding="utf-8-sig"))
    jsonschema.validate(instance=seed, schema=schema)


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_minor_soeum_prunes_hiit_and_if() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.integrated_wellness_solution_v2_core import load_json, resolve_integrated_wellness

    seed = load_json(SEED)
    resolved = resolve_integrated_wellness(seed, lexicon_path=LEXICON)

    suppressed_ids = {e["node_id"] for e in resolved.get("suppression_log", [])}
    assert "hiit_high_intensity_sweat" in suppressed_ids
    assert "if_16_8" in suppressed_ids

    resolved_ids = {n["node_id"] for n in resolved.get("resolved_evidence_stream", [])}
    assert "hiit_high_intensity_sweat" not in resolved_ids
    assert "if_16_8" not in resolved_ids
    assert "action_minor_regular_meals" in resolved_ids
    assert "action_low_intensity_lower_body" in resolved_ids
    assert "biomech_zoa_adim" in resolved_ids


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_adult_profile_suppresses_minor_only_nodes() -> None:
    import copy

    sys.path.insert(0, str(ROOT))
    from scripts.integrated_wellness_solution_v2_core import load_json, resolve_integrated_wellness

    seed = copy.deepcopy(load_json(SEED))
    seed["client_profile"].update(
        {
            "birth_instant_utc": "1988-03-11T15:00:00Z",
            "computed_age_band": "young_adult",
            "growth_phase": False,
        }
    )
    resolved = resolve_integrated_wellness(seed, lexicon_path=LEXICON)

    suppressed_ids = {e["node_id"] for e in resolved.get("suppression_log", [])}
    for minor_id in (
        "policy_minor_no_if",
        "policy_minor_no_hiit",
        "action_minor_regular_meals",
        "action_low_intensity_lower_body",
    ):
        assert minor_id in suppressed_ids, f"expected {minor_id} suppressed for adult"

    resolved_ids = {n["node_id"] for n in resolved.get("resolved_evidence_stream", [])}
    assert "policy_minor_no_if" not in resolved_ids
    assert "action_minor_regular_meals" not in resolved_ids

    for node in resolved.get("resolved_evidence_stream", []):
        title = (node.get("content_payload") or {}).get("title") or ""
        body = (node.get("content_payload") or {}).get("body") or ""
        assert "성장기" not in title, f"adult stream must not include 성장기 title: {title}"
        assert "성장기" not in body or node["node_id"] == "myeongni_temporal_stub", node["node_id"]


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_minor_soeum_maps_a_code_restore() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.integrated_wellness_solution_v2_core import load_json, resolve_integrated_wellness

    seed = load_json(SEED)
    resolved = resolve_integrated_wellness(seed, lexicon_path=LEXICON)
    assert resolved["client_profile"].get("a_code_consumer") == "A-12"
    consumer = resolved["lexicon_profile"]["consumer_a_code"]
    assert consumer["display_name_ko"] == "회복 리스토어"


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_chain_smoke_exit_zero(tmp_path: Path) -> None:
    out_dir = tmp_path / "chain"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_integrated_wellness_solution_v2_chain_v1.py"),
            "--seed-json",
            str(SEED),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert (out_dir / "resolved_latest.json").is_file()
    assert (out_dir / "render_no1kmedi_latest.json").is_file()
    no1 = json.loads((out_dir / "render_no1kmedi_latest.json").read_text(encoding="utf-8"))
    assert no1.get("human_confirm_required") is True
    slots = no1.get("patient_slots") or []
    assert any(s.get("slot_id") == "sasang" for s in slots)
    assert isinstance(no1.get("suppression_log"), list)
    assert no1.get("suppression_log_count") == len(no1["suppression_log"])


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_seed_builder_patches_myeongni_from_consult(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.build_integrated_wellness_seed_from_consult_v1 import build_seed

    consult = {
        "request_id": "pytest_myeongni",
        "lane_a_profile": {
            "birth_instant_utc": "2010-06-15T03:30:00Z",
            "iana_tz": "Asia/Seoul",
        },
        "lane_b_clinical": {"chief_complaint": "복부 비만"},
        "gender": "female",
    }
    seed = build_seed(consult, template_path=SEED)
    node = next(n for n in seed["evidence_nodes_seed"] if n["node_id"] == "myeongni_temporal_stub")
    assert node["source_ref"] == "manseryeok_perfect_final_v1"
    body = node["content_payload"]["body"]
    assert "사주" in body or "四柱" in body
    assert "명리" in node["content_payload"]["title"]
    assert "오행" in node["content_payload"]["body"]


@pytest.mark.skipif(not SEED.is_file(), reason="seed missing")
def test_personadiary_adapter_produces_ui_blocks(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.integrated_wellness_solution_v2_core import load_json, resolve_integrated_wellness
    from scripts.render_integrated_wellness_solution_v2 import render_personadiary

    seed = load_json(SEED)
    resolved = resolve_integrated_wellness(seed, lexicon_path=LEXICON)
    render_doc = render_personadiary(resolved)

    adapt_script = ROOT / "scripts" / "adapt_integrated_wellness_personadiary_export_v1.py"
    out_json = tmp_path / "pd_pkg.json"
    (tmp_path / "render.json").write_text(json.dumps(render_doc, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "resolved.json").write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(adapt_script),
            "--render-json",
            str(tmp_path / "render.json"),
            "--resolved-json",
            str(tmp_path / "resolved.json"),
            "--out-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    pkg = json.loads(out_json.read_text(encoding="utf-8"))
    assert pkg["schema"] == "personadiary_daily_response_package_v1"
    assert len(pkg["ui_blocks"]) >= 2
    assert any(b.get("type") == "hero" for b in pkg["ui_blocks"])
    assert any("몸·리듬" in (b.get("title_ko") or "") for b in pkg["ui_blocks"])
    assert any("명리 참고" in (b.get("title_ko") or "") for b in pkg["ui_blocks"])


@pytest.mark.skipif(not LEXICON.is_file(), reason="lexicon missing")
def test_a_code_lexicon_has_twelve_entries() -> None:
    lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries = lex.get("entries") or []
    assert len(entries) == 12
    codes = {e["code_id"] for e in entries}
    assert codes == {f"A-{i:02d}" for i in range(1, 13)}
