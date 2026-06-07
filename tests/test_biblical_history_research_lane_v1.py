# Keywords: biblical_history_research_lane, H-BC1, walkforward

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDEcar = ROOT / "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"
WALKFORWARD = ROOT / "docs/final/artifacts/logos_falsification_walkforward_latest.json"
NEWS_SMOKE = ROOT / "tests/fixtures/biblical_resonance_research_news_smoke_v1.jsonl"


def test_h_pr1_and_h_ar1_chronology_sidecars() -> None:
    pr1 = ROOT / "docs/final/artifacts/biblical_history_h_pr1_printing_info_disruption_chronology_sidecar_v1.json"
    ar1 = ROOT / "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json"
    for path, hyp_id, epoch_key in (
        (pr1, "H-PR1", "epoch_window_ce"),
        (ar1, "H-AR1", "epoch_window_bce"),
    ):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("hypothesis_id") == hyp_id
        assert doc.get("gating_status") == "NON_GATING"
        assert isinstance(doc.get("nodes"), list) and len(doc["nodes"]) >= 4
        assert isinstance(doc.get(epoch_key), dict)


def test_h_dss1_chronology_sidecar() -> None:
    dss1 = ROOT / "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json"
    doc = json.loads(dss1.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-DSS1"
    assert doc.get("gating_status") == "NON_GATING"
    assert doc.get("corpus_type") == "dss"
    assert isinstance(doc.get("epoch_window_bce"), dict)
    assert isinstance(doc.get("epoch_window_ce"), dict)
    nodes = doc.get("nodes")
    assert isinstance(nodes, list) and len(nodes) >= 5
    ce_nodes = [n for n in nodes if isinstance(n, dict) and isinstance(n.get("date_ce_mid"), int)]
    bce_nodes = [n for n in nodes if isinstance(n, dict) and isinstance(n.get("date_bce_mid"), int)]
    assert len(ce_nodes) >= 2
    assert len(bce_nodes) >= 2


def test_h_dss1_bce_and_ce_epoch_permutation_runs() -> None:
    dss_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json"
    for era, out_name in (
        ("bce", "biblical_history_h_dss1_epoch_permutation_latest.json"),
        ("ce", "biblical_history_h_dss1_ce_epoch_permutation_latest.json"),
    ):
        out = ROOT / "reports" / out_name
        cmd = [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(dss_sidecar),
            "--era",
            era,
            "--permutation-repeats",
            "100",
        ]
        if era == "ce":
            cmd += ["--output-json", str(out)]
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        assert r.returncode == 0, r.stderr + r.stdout
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc.get("hypothesis_id") == "H-DSS1"
        assert doc.get("era") == era
        assert doc["observed"]["node_count"] >= 2


def test_cosmological_calibration_smoke_runs() -> None:
    out = ROOT / "reports/biblical_history_cosmological_calibration_smoke_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_biblical_history_cosmological_epoch_calibration_v1.py"),
            "--hypothesis-id",
            "H-BC1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_cosmological_calibration_smoke_v1"
    assert doc.get("hypothesis_tier") == "[HYPO]"
    assert doc.get("research_rail") == "B"


def test_h_ax1_and_h_pl1_chronology_sidecars() -> None:
    ax1 = ROOT / "docs/final/artifacts/biblical_history_h_ax1_axial_age_chronology_sidecar_v1.json"
    pl1 = ROOT / "docs/final/artifacts/biblical_history_h_pl1_plague_chronology_sidecar_v1.json"
    for path, hyp_id in ((ax1, "H-AX1"), (pl1, "H-PL1")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("hypothesis_id") == hyp_id
        assert doc.get("gating_status") == "NON_GATING"
        assert isinstance(doc.get("nodes"), list) and len(doc["nodes"]) >= 4


def test_h_ax1_epoch_permutation_runs() -> None:
    ax1_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_ax1_axial_age_chronology_sidecar_v1.json"
    out = ROOT / "reports/biblical_history_h_ax1_epoch_permutation_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(ax1_sidecar),
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-AX1"
    assert doc.get("schema") == "biblical_history_h_ax1_epoch_permutation_v1"
    assert doc["sliding_window_null"]["window_width_bce_years"] == 600
    assert doc["observed"]["nodes_in_epoch_window"] >= 4


def test_h_pr1_ce_epoch_permutation_runs() -> None:
    pr1_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_pr1_printing_info_disruption_chronology_sidecar_v1.json"
    out = ROOT / "reports/biblical_history_h_pr1_epoch_permutation_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(pr1_sidecar),
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-PR1"
    assert doc.get("era") == "ce"
    assert doc["sliding_window_null"]["window_width_ce_years"] == 570
    assert doc["observed"]["nodes_in_epoch_window"] >= 4


def test_h_ar1_ce_epoch_permutation_runs() -> None:
    ar1_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json"
    out = ROOT / "reports/biblical_history_h_ar1_ce_epoch_permutation_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(ar1_sidecar),
            "--era",
            "ce",
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-AR1"
    assert doc.get("era") == "ce"
    assert doc["observed"]["node_count"] == 2
    assert doc["observed"]["nodes_in_epoch_window"] == 2


def test_h_ar1_adna_events_join_runs() -> None:
    out = ROOT / "reports/biblical_history_h_ar1_adna_events_join_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/join_biblical_history_h_ar1_adna_events_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-AR1"
    assert doc["summary"]["peer_event_matches"] >= 4


def test_h_ar1_bce_epoch_permutation_runs() -> None:
    ar1_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json"
    out = ROOT / "reports/biblical_history_h_ar1_epoch_permutation_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(ar1_sidecar),
            "--era",
            "bce",
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-AR1"
    assert doc.get("era") == "bce"
    assert doc["observed"]["node_count"] == 3
    assert doc["observed"]["nodes_in_epoch_window"] == 3


def test_dss_apocrypha_research_context_ingest_runs() -> None:
    out = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ingest_dss_apocrypha_research_context_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 8
    sample = json.loads(rows[0])
    assert sample.get("hypothesis_tag") == "[HYPO]"
    assert sample.get("corpus_type") == "dss"


def test_h_dss1_chronicle_overlay_and_hold_alignment() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/ingest_dss_apocrypha_research_context_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    r1 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_chronicle_h_dss1_daily_overlay_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    overlay = ROOT / "docs/final/artifacts/chronicle_history_news_signal_h_dss1_daily_overlay_latest.jsonl"
    overlay_rows = [ln for ln in overlay.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(overlay_rows) >= 1
    r2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_biblical_history_h_dss1_chronicle_hold_alignment_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    doc = json.loads(
        (ROOT / "reports/biblical_history_h_dss1_chronicle_hold_alignment_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("hypothesis_id") == "H-DSS1"
    assert doc["inputs"]["chronicle_overlay_row_count"] >= 1


def test_chronicle_research_decision_mix_builds() -> None:
    out = ROOT / "docs/final/artifacts/chronicle_history_news_signal_research_decision_mix_latest.jsonl"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_chronicle_history_research_decision_mix_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out.is_file()
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    decisions = {str(row.get("final_decision", "")).upper() for row in rows}
    assert decisions.issubset({"HOLD", "WATCH", "REDUCE"})
    assert len(decisions) >= 2


def test_h_dss1_chronicle_epoch_shuffle_negative_control_runs() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_chronicle_history_research_decision_mix_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    out = ROOT / "reports/biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_v1.py"),
            "--shuffle-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-DSS1"
    assert "permutation_p_values" in doc
    assert "composite_score" in doc.get("observed", {})
    pvals = doc["permutation_p_values"]
    assert "composite_score_ge_observed_decision_shuffle" in pvals
    assert "composite_score_ge_observed_keyword_null" in pvals
    assert doc["inputs"]["chronicle_source_used"].endswith("research_decision_mix_latest.jsonl")
    counts = doc["inputs"]["chronicle_final_decision_counts"]
    assert counts.get("WATCH", 0) + counts.get("REDUCE", 0) >= 1
    assert doc["permutation_p_values"]["composite_score_two_sided_decision_shuffle"] < 1.0
    assert doc["permutation_p_values"]["composite_score_two_sided_keyword_null"] < 1.0


def test_holdout_brier_dual_report_runs() -> None:
    out = ROOT / "reports/biblical_history_holdout_brier_dual_report_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_biblical_history_holdout_brier_dual_report_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_holdout_brier_dual_report_v1"
    assert doc["production_hist_only"]["n_evaluated"] == 8
    anchor = doc["h_dss1_holdout_anchor"]
    assert anchor["in_production_registry"] is True
    assert anchor["sandbox_row"]["question_id"] == "hist.arch.dead_sea_scrolls_cave1_1947"
    assert anchor["production_hist_row"]["question_id"] == "hist.arch.dead_sea_scrolls_cave1_1947"
    assert anchor["sandbox_row"]["brier_contribution"] == anchor["production_hist_row"]["brier_contribution"]
    assert anchor["brier_delta_production_minus_sandbox"] == 0.0
    assert len(doc["hist_per_question"]) == 8
    assert doc["hist_per_question_all_aligned"] is True


def test_dss_apocrypha_frontline_rebuild_dry_run() -> None:
    latest = ROOT / "reports/dss_apocrypha_frontline_rebuild_chain_latest.json"
    latest_before = latest.read_text(encoding="utf-8") if latest.is_file() else None
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_dss_apocrypha_frontline_rebuild_chain_v1.py"),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    ext2 = ROOT / "reports/tmp_dss_apocrypha_dry_run/apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson"
    assert ext2.is_file()
    lines = [ln for ln in ext2.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 3
    dry_report = ROOT / "reports/dss_apocrypha_frontline_rebuild_chain_dry_run_latest.json"
    assert dry_report.is_file()
    dry_doc = json.loads(dry_report.read_text(encoding="utf-8"))
    assert dry_doc.get("dry_run") is True
    ssot = dry_doc.get("on_disk_corpus_ssot") or {}
    assert ssot.get("ext2_weighted_lines", 0) >= 1000
    assert ssot.get("ext3_hebrew_priority_lines", 0) >= 1000
    if latest_before is not None:
        assert latest.read_text(encoding="utf-8") == latest_before


def test_dss_frontline_research_bridge_runs() -> None:
    out = ROOT / "reports/dss_frontline_research_bridge_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_dss_frontline_research_bridge_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "dss_frontline_research_bridge_v1"
    assert doc.get("recommendation") in (
        "run_frontline_in_dss_project_root",
        "watch_missing_dss_ingest_scripts_use_smoke_bootstrap",
    )


def test_dss_ndjson_resonance_uplift_report_runs() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_biblical_resonance_research_production_ab_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    out = ROOT / "reports/dss_ndjson_resonance_uplift_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_dss_ndjson_resonance_uplift_report_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "dss_ndjson_resonance_uplift_v1"
    assert "delta_prod_plus_ndjson_minus_production" in doc


def test_dss_authority_readiness_reconciliation_runs() -> None:
    out = ROOT / "reports/dss_authority_readiness_reconciliation_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_dss_authority_readiness_reconciliation_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "dss_authority_readiness_reconciliation_v1"
    assert doc["ext3_pin"]["status"] in ("READY", "BLOCKED", "MISSING", "UNKNOWN")
    assert "ingest_recommendation" in doc


def test_dss_ndjson_token_manifest_ingest_watch_without_files() -> None:
    out = ROOT / "reports/tmp_dss_ndjson_watch_test.jsonl"
    missing = ROOT / "reports/nonexistent_dss_ndjson_watch_test_v1.ndjson"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"),
            "--ndjson-path",
            str(missing),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert any("ingest gate" in str(row.get("canonical_text", "")).lower() for row in rows)


def test_evaluate_authority_readiness_ext3_refresh_ready() -> None:
    dss = ROOT / "projects/dss-4d-ingest"
    fusion = dss / "outputs/fusion_join_quality_command_center_followup_20260607_ext3_refresh.json"
    quality = dss / "outputs/apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json"
    if not fusion.is_file() or not quality.is_file():
        pytest.skip("ext3 fusion/quality artifacts missing")
    insight = ROOT / "reports/tmp_authority_insight_brief_test.json"
    authority = ROOT / "reports/tmp_authority_readiness_test.json"
    subprocess.run(
        [
            sys.executable,
            str(dss / "build_dss_apocrypha_insight_brief_v1.py"),
            "--tag",
            "test_ext3",
            "--quality-json",
            str(quality),
            "--fusion-quality-json",
            str(fusion),
            "--out-json",
            str(insight),
        ],
        cwd=str(dss),
        check=True,
    )
    r = subprocess.run(
        [
            sys.executable,
            str(dss / "evaluate_authority_readiness.py"),
            "--tag",
            "test_ext3",
            "--insight-brief-json",
            str(insight),
            "--out-json",
            str(authority),
        ],
        cwd=str(dss),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(authority.read_text(encoding="utf-8"))
    assert doc.get("status") == "READY"
    assert doc.get("checks", {}).get("fusion_overlap_ratio_dss") is True


def test_dss_ndjson_token_manifest_full_surface_chunk_with_fixture() -> None:
    auth = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
    fixture = ROOT / "tests/fixtures/dss_tokens_research_smoke_v1.ndjson"
    out = ROOT / "reports/tmp_dss_ndjson_full_surface_test.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"),
            "--authority-json",
            str(auth),
            "--ndjson-path",
            str(fixture),
            "--ingest-mode",
            "full_surface_chunk",
            "--chunk-size",
            "2",
            "--max-surface-rows-per-file",
            "20",
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 3
    assert any("token surface chunk" in str(row.get("canonical_text", "")).lower() for row in rows)
    assert all("token_text" not in str(row.get("canonical_text", "")) for row in rows)


def test_dss_ndjson_token_manifest_ingest_summary_with_fixture() -> None:
    auth = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
    fixture = ROOT / "tests/fixtures/dss_tokens_research_smoke_v1.ndjson"
    out = ROOT / "reports/tmp_dss_ndjson_research_context_test.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"),
            "--authority-json",
            str(auth),
            "--ndjson-path",
            str(fixture),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any("corpus manifest" in str(row.get("canonical_text", "")).lower() for row in rows)
    assert any("apocrypha" in str(row.get("canonical_text", "")).lower() for row in rows)
    assert all("token_text" not in str(row.get("canonical_text", "")) for row in rows)


def test_bootstrap_dss_ndjson_research_paths_smoke() -> None:
    target = ROOT / "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson"
    backup_exists = target.is_file()
    backup_bytes = target.read_bytes() if backup_exists else None
    try:
        if target.is_file():
            target.unlink()
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/bootstrap_dss_ndjson_research_paths_v1.py"),
                "--allow-smoke-bootstrap",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        assert target.is_file()
        rep = json.loads((ROOT / "reports/dss_ndjson_research_bootstrap_latest.json").read_text(encoding="utf-8"))
        assert rep.get("status") == "smoke_bootstrapped"
    finally:
        if backup_exists and backup_bytes is not None:
            target.write_bytes(backup_bytes)
        elif target.is_file():
            target.unlink()


def test_biblical_resonance_research_production_ab_runs() -> None:
    tmp_ndjson = ROOT / "reports/tmp_biblical_ab_test_ndjson_context.jsonl"
    tmp_slice = ROOT / "reports/tmp_biblical_ab_test_research_slice.jsonl"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/ingest_dss_apocrypha_research_context_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"),
            "--ndjson-path",
            str(ROOT / "tests/fixtures/dss_tokens_research_smoke_v1.ndjson"),
            "--output-jsonl",
            str(tmp_ndjson),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/refresh_biblical_history_news_observation_slice_v1.py"),
            "--max-korea-rows",
            "10",
            "--output-jsonl",
            str(tmp_slice),
            "--ndjson-context-jsonl",
            str(tmp_ndjson),
        ],
        cwd=str(ROOT),
        check=True,
    )
    out = ROOT / "reports/tmp_biblical_ab_test_production_ab.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_biblical_resonance_research_production_ab_v1.py"),
            "--research-slice-jsonl",
            str(tmp_slice),
            "--ndjson-context-jsonl",
            str(tmp_ndjson),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-DSS1"
    assert "delta_research_slice_minus_production" in doc
    assert "research_slice_plus_ndjson_context" in doc["arms"]
    assert "production_plus_ndjson_context" in doc["arms"]
    assert "delta_slice_plus_ndjson_minus_research_slice" in doc


def test_holdout_merge_readiness_dry_run() -> None:
    out = ROOT / "reports/biblical_history_holdout_merge_readiness_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_biblical_history_holdout_merge_readiness_v1.py"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_holdout_merge_readiness_v1"
    assert "h_dss1_holdout_anchor" in doc


def test_chronicle_pr1_daily_overlay_and_hold_alignment() -> None:
    r1 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_chronicle_pr1_daily_overlay_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    overlay = ROOT / "docs/final/artifacts/chronicle_history_news_signal_pr1_daily_overlay_latest.jsonl"
    rows = [ln for ln in overlay.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 1
    r2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_biblical_history_h_pr1_chronicle_hold_alignment_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    doc = json.loads((ROOT / "reports/biblical_history_h_pr1_chronicle_hold_alignment_latest.json").read_text(encoding="utf-8"))
    assert doc["inputs"]["chronicle_overlay_row_count"] >= 1
    assert doc["metrics"]["pr1_news_days_with_chronicle_overlap"] >= 1


def test_h_pr1_chronicle_hold_alignment_runs() -> None:
    out = ROOT / "reports/biblical_history_h_pr1_chronicle_hold_alignment_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_biblical_history_h_pr1_chronicle_hold_alignment_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-PR1"
    assert "chronicle_hold_rate" in doc.get("metrics", {})


def test_h_pl1_lexicon_uplift_fixture_positive() -> None:
    out = ROOT / "reports/biblical_history_h_pl1_lexicon_uplift_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_biblical_history_h_pl1_lexicon_uplift_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("hypothesis_id") == "H-PL1"
    assert doc["summary"]["fixture_2026_uplift_positive"] is True
    assert doc["summary"]["fixture_2026_covid_window_match_ratio"] > doc["summary"]["fixture_2026_control_window_match_ratio"]


def test_h_bc1_sliding_window_permutation_fields() -> None:
    bc1_sidecar = ROOT / "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
            "--sidecar-json",
            str(bc1_sidecar),
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((ROOT / "reports/biblical_history_h_bc1_epoch_permutation_latest.json").read_text(encoding="utf-8"))
    assert "sliding_window_null" in doc
    pvals = doc.get("permutation_p_values") or {}
    assert "sliding_window_max_ge_observed" in pvals
    assert doc["sliding_window_null"].get("window_width_bce_years") is not None


def test_h_bc1_chronology_sidecar_skeleton() -> None:
    assert SIDEcar.is_file(), f"missing {SIDEcar}"
    doc = json.loads(SIDEcar.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_chronology_sidecar_v1"
    assert doc.get("hypothesis_id") == "H-BC1"
    assert doc.get("gating_status") == "NON_GATING"
    nodes = doc.get("nodes")
    assert isinstance(nodes, list) and len(nodes) >= 4
    assert doc.get("network_metrics_stub", {}).get("multi_node_collapse_count_in_window", 0) >= 4


def test_logos_falsification_walkforward_artifact_has_oos_folds() -> None:
    if not WALKFORWARD.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_logos_falsification_walkforward_v1.py")],
            cwd=str(ROOT),
            check=True,
        )
    doc = json.loads(WALKFORWARD.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_falsification_walkforward_v1"
    folds = doc.get("walkforward_folds", {})
    assert "logos_primary_oos" in folds
    assert doc.get("mean_oos_fold_hit_rate", {}).get("logos_primary_oos") is not None


def test_biblical_resonance_eval_counts_chronicle_generated_at_utc() -> None:
    """Regression: chronicle history rows timestamp field is generated_at_utc."""
    chronicle = ROOT / "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl"
    if not chronicle.is_file():
        return
    out = ROOT / "reports/biblical_resonance_eval_chronicle_ts_regression_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_biblical_resonance_hypotheses_v1.py"),
            "--lookback-days",
            "365",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["inputs"]["chronicle_row_count"] >= 1


def test_biblical_resonance_research_smoke_eval_nonzero() -> None:
    assert NEWS_SMOKE.is_file()
    out = ROOT / "reports/biblical_resonance_eval_research_smoke_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_biblical_resonance_hypotheses_v1.py"),
            "--news-jsonl",
            str(NEWS_SMOKE),
            "--lookback-days",
            "90",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["inputs"]["news_row_count"] >= 3
    hyps = doc.get("hypotheses") or []
    assert len(hyps) >= 5
    bc1 = next(h for h in hyps if h.get("id") == "H-BC1")
    assert bc1.get("matched_rows", 0) >= 1


def test_h_bc1_epoch_permutation_eval_runs() -> None:
    out = ROOT / "reports/biblical_history_h_bc1_epoch_permutation_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"), "--permutation-repeats", "200"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "biblical_history_h_bc1_epoch_permutation_v1"
    assert doc.get("observed", {}).get("nodes_in_epoch_window", 0) >= 4
    pvals = doc.get("permutation_p_values") or {}
    assert "span_clustering_le_observed" in pvals


def test_h_bc1_paleoclimate_join_runs() -> None:
    out = ROOT / "reports/biblical_history_h_bc1_paleoclimate_join_latest.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/join_biblical_history_h_bc1_paleoclimate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("summary", {}).get("proxy_matches", 0) >= 4


def test_holdout_merge_signoff_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/merge_biblical_history_holdout_to_general_prophecy_v1.py"), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(r.stdout.strip().splitlines()[-1])
    assert doc.get("dry_run") is True
    before_count = int(doc.get("before_count", 0))
    after_count = int(doc.get("after_count", 0))
    assert after_count >= before_count
    would_add = doc.get("would_add") or []
    assert after_count == before_count + len(would_add)


def test_health_articles_ingest_source_id_prefix(tmp_path: Path) -> None:
    health = ROOT / "reports/korea_health_infectious_news_articles_v1.json"
    if not health.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_korea_health_infectious_news_context_v1.py"), "--skip-naver"],
            cwd=str(ROOT),
            check=True,
        )
    out_jsonl = tmp_path / "news_observation_health_ingest.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest_korea_context_to_news_observation_v1.py"),
            "--articles-json",
            str(health),
            "--output-jsonl",
            str(out_jsonl),
            "--source-id-prefix",
            "korea_health",
            "--dataset-partition",
            "train_holdout",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [json.loads(ln) for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 1
    assert all(str(row.get("source_id", "")).startswith("korea_health_") for row in rows)
    assert all(row.get("dataset_partition") == "train_holdout" for row in rows)


def test_dss_research_lane_handoff_builds() -> None:
    out = ROOT / "reports/tmp_dss_research_lane_handoff_test.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_dss_research_lane_handoff_v1.py"), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "dss_research_lane_handoff_v1"
    assert doc.get("research_rail") == "B"
    assert doc.get("track_a_promotion") == "blocked"
    assert doc.get("guidance", {}).get("recommended_ndjson_profile") in ("ext3_only", "default_3file_max_coverage")


def test_dss_ext3_chunk_size_sweep_smoke() -> None:
    out = ROOT / "reports/tmp_dss_ext3_chunk_sweep_test.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_dss_ext3_only_chunk_size_sweep_v1.py"),
            "--chunk-sizes",
            "40,50",
            "--max-surface-rows-per-file",
            "200",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "dss_ext3_only_chunk_size_sweep_v1"
    assert doc.get("best_chunk_size") in (40, 50)
    assert int(doc.get("best_row_count") or 0) >= 1


def test_unified_frontline_legacy_scripts_smoke() -> None:
    dss = ROOT / "projects/dss-4d-ingest"
    tag = "pytest_legacy_smoke"
    fusion = dss / "outputs/fusion_join_quality_command_center_followup_20260607_unified_rebuild.json"
    insight = dss / "outputs/dss_apocrypha_insight_brief_command_center_followup_20260607_unified_rebuild.json"
    authority = dss / "outputs/authority_readiness_command_center_followup_20260607_unified_rebuild.json"
    if not fusion.is_file() or not insight.is_file() or not authority.is_file():
        return
    steps = [
        (
            "run_joint_frontline_gate.py",
            ["--tag", tag, "--fusion-json", str(fusion), "--authority-json", str(authority)],
        ),
        ("summarize_dss_apocrypha_insights.py", ["--tag", tag, "--insight-brief-json", str(insight)]),
        ("plan_apocrypha_hebrew_priority.py", ["--tag", tag]),
        ("rank_apocrypha_symbol_patterns.py", ["--tag", tag]),
        ("generate_fusion_rule_candidates.py", ["--tag", tag, "--fusion-json", str(fusion)]),
    ]
    for script, extra in steps:
        r = subprocess.run([sys.executable, str(dss / script), *extra], cwd=str(dss), capture_output=True, text=True)
        assert r.returncode == 0, f"{script}: {r.stderr}{r.stdout}"


def test_biblical_history_news_research_slice_refresh() -> None:
    out_jsonl = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/refresh_biblical_history_news_observation_slice_v1.py"),
            "--max-korea-rows",
            "20",
            "--run-resonance-eval",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rows = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 5
    eval_doc = json.loads((ROOT / "reports/biblical_resonance_eval_research_slice_latest.json").read_text(encoding="utf-8"))
    assert eval_doc["inputs"]["news_row_count"] >= 5


def test_biblical_history_research_slice_decoupled_skip_korea_context() -> None:
    out_jsonl = ROOT / "reports/tmp_biblical_research_slice_decoupled_skip_korea.jsonl"
    ab_out = ROOT / "reports/tmp_biblical_isolated_ab_slice_decoupled_skip_korea.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/refresh_biblical_history_news_observation_slice_v1.py"),
            "--skip-ndjson-context",
            "--skip-korea-context",
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip().splitlines()[-1])
    assert summary["slice_flags"]["skip_korea_context"] is True
    rows = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 1
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_biblical_resonance_isolated_production_ab_v1.py"),
            "--research-slice-jsonl",
            str(out_jsonl),
            "--output-json",
            str(ab_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    doc = json.loads(ab_out.read_text(encoding="utf-8"))
    assert doc["isolation"]["removed_overlap_slice_keys"] == 0
