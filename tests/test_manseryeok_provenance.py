from __future__ import annotations

from pathlib import Path

from tools.myeongni.manseryeok_provenance import (
    approx_stub_pipeline_metadata,
    btrack_myeongni_16_state_stream_scope,
    btrack_pilot_bench_scope,
    enrich_record_optional_solar_provenance,
    jeolgi_boundary_risk_day,
    load_bench_manseryeok_scope_manifest,
    load_manse_precision_runtime_pointer,
    logos_myeongni_state_join_scope,
    multilens_p1_compression_scope,
    myeongni_row_provenance,
    resolve_bench_row_manseryeok_scope,
    tag_excluded_from_jaccard_heuristic,
    upsert_bench_manseryeok_scope_manifest,
)


def test_jeolgi_boundary_risk_centered() -> None:
    assert jeolgi_boundary_risk_day(2, 4, window_days=1) is True
    assert jeolgi_boundary_risk_day(2, 3, window_days=1) is True
    assert jeolgi_boundary_risk_day(2, 5, window_days=1) is True
    assert jeolgi_boundary_risk_day(2, 6, window_days=1) is False


def test_jeolgi_boundary_invalid_month() -> None:
    assert jeolgi_boundary_risk_day(0, 5) is False
    assert jeolgi_boundary_risk_day(13, 5) is False


def test_tag_excluded_respects_engine_flag() -> None:
    assert tag_excluded_from_jaccard_heuristic(2, 4, engine_is_approx=False) is False
    assert tag_excluded_from_jaccard_heuristic(2, 4, engine_is_approx=True) is True


def test_approx_metadata_keys() -> None:
    m = approx_stub_pipeline_metadata()
    assert m["manseryeok_model"] == "static_month_day_approx_v3"
    assert m["jeolgi_uncertainty"] == "boundary_days_high_risk"
    assert "manseryeok_provenance_note" in m


def test_multilens_p1_fence() -> None:
    f = multilens_p1_compression_scope()
    assert f["manseryeok_applicable"] is False
    assert f["jaccard_metric_domain"] == "compression_token_reconstruction"


def test_logos_join_scope() -> None:
    s = logos_myeongni_state_join_scope()
    assert s["manseryeok_applicable"] is False
    assert "cosine" in s["artifact_domain"]


def test_btrack_16_state_scope() -> None:
    s = btrack_myeongni_16_state_stream_scope()
    assert s["manseryeok_pillar_calc_applicable"] is False


def test_btrack_pilot_bench_scope() -> None:
    s = btrack_pilot_bench_scope(build_script="x.py", source_note="note")
    assert s["artifact_domain"] == "btrack_pilot_bench_jsonl"
    assert s["build_script"] == "x.py"
    assert "note" in s["manseryeok_scope_note"]


def test_upsert_bench_manifest_merges(tmp_path: Path) -> None:
    root = tmp_path
    upsert_bench_manseryeok_scope_manifest(root, "ref_a", {"k": 1})
    upsert_bench_manseryeok_scope_manifest(root, "ref_b", {"k": 2})
    m = load_bench_manseryeok_scope_manifest(root)
    assert m is not None
    assert m["schema"] == "btrack_bench_manseryeok_scope_manifest_v1"
    assert m["scopes"]["ref_a"]["k"] == 1
    assert m["scopes"]["ref_b"]["k"] == 2


def test_resolve_bench_row_inline_and_ref() -> None:
    full = {"manseryeok_scope_ref": "r1"}
    manifest = {"scopes": {"r1": {"artifact_domain": "x"}}}
    assert resolve_bench_row_manseryeok_scope({"manseryeok_scope": {"inline": True}})["inline"] is True
    assert resolve_bench_row_manseryeok_scope(full, manifest=manifest)["artifact_domain"] == "x"
    assert resolve_bench_row_manseryeok_scope(full, manifest=None) is None


def test_enrich_optional_solar() -> None:
    base = {"hypothesis_tier": "B", "boundary_ack": True, "stub": False}
    r = enrich_record_optional_solar_provenance(base, solar_month=None, solar_day=None)
    assert "manseryeok_provenance" not in r
    r2 = enrich_record_optional_solar_provenance(base, solar_month=3, solar_day=5)
    assert "manseryeok_provenance" in r2


def test_myeongni_row_provenance_merges_excluded() -> None:
    r = myeongni_row_provenance(2, 4, engine_is_approx=True)
    assert r["excluded_from_jaccard"] is True
    assert r["manseryeok_model"] == "static_month_day_approx_v3"
    r2 = myeongni_row_provenance(6, 1, engine_is_approx=False)
    assert r2["excluded_from_jaccard"] is False
    assert r2["manseryeok_model"] == "precision_engine_unspecified"
    assert "Path B" in r2["manseryeok_provenance_note"]


def test_load_manse_precision_pointer_from_repo_root() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    doc = load_manse_precision_runtime_pointer(root)
    assert doc is not None
    assert doc.get("schema") == "manse_precision_runtime_pointer_v1"
