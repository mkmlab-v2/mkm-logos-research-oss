# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke CSV→JSONL→triplet registry (no network).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_CHAIN = _ROOT / "scripts" / "run_weather_gt_to_prophecy_triplet_chain_v1.py"
_CSV = _ROOT / "scripts" / "csv_to_weather_ground_truth_jsonl_v1.py"
_TRIPLET = _ROOT / "scripts" / "build_weather_triplet_registry_v1.py"
_VALIDATE = _ROOT / "scripts" / "validate_weather_ground_truth_jsonl_v1.py"
_SIDECAR = _ROOT / "scripts" / "weather_gt_jsonl_to_forecasts_sidecar_v1.py"
_SAMPLE_GT_JSONL = _ROOT / "tests" / "fixtures" / "weather_ground_truth_rows_v1.sample.jsonl"
_SYNTHETIC_JSONL = _ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_v1.jsonl"
_MINIMAL_CSV = _ROOT / "tests" / "fixtures" / "weather_ground_truth_minimal_input.csv"
_COMMITTED_REGISTRY = _ROOT / "tests" / "fixtures" / "weather_prophecy_triplet_chain_smoke_v1.json"
_SYNTH120_RUNNER = _ROOT / "scripts" / "run_weather_synthetic_120d_chain_and_brier_v1.py"
_SNIFF = _ROOT / "scripts" / "weather_csv_sniff_v1.py"
_KAGGLE_SNIFF_CSV = _ROOT / "tests" / "fixtures" / "weather_kaggle_style_sniff_input.csv"
_EXTERNAL_FORECASTS_JSONL = _ROOT / "tests" / "fixtures" / "weather_forecasts_external_lens_minimal_v1.jsonl"
_EXTERNAL_120_HYPO_JSONL = _ROOT / "tests" / "fixtures" / "weather_synthetic_120d_external_lens_hypo_v1.jsonl"
_VALIDATE_FC = _ROOT / "scripts" / "validate_weather_forecasts_jsonl_against_gt_v1.py"
_EMIT_FC = _ROOT / "scripts" / "emit_weather_forecasts_jsonl_template_from_gt_v1.py"
_OPTIM_FUSION = _ROOT / "scripts" / "optimize_weather_lens_fusion_weights_v1.py"
_BTRACK_ARTIFACT_RUNNER = _ROOT / "scripts" / "run_weather_btrack_hypo_fusionopt_to_artifacts_v1.py"
_BTRACK_EXTERNAL_RUNNER = _ROOT / "scripts" / "run_weather_btrack_external_forecasts_to_artifacts_v1.py"
_BTRACK_EXTERNAL_REAL_WEEK_PS1 = _ROOT / "scripts" / "run_weather_btrack_external_real_week_chain_v1.ps1"
_BTRACK_EXTERNAL_REAL_WEEK_FULL_GATE_PS1 = _ROOT / "scripts" / "run_weather_btrack_external_real_week_full_gate_v1.ps1"


def test_committed_weather_btrack_hypo_fusionopt_summary_schema() -> None:
    """HYPO 융합 최적화 요약 아티팩트(재생성 스크립트 산출) 스키마 고정."""
    p = _ROOT / "docs" / "final" / "artifacts" / "weather_btrack_pipeline_hypo_fusionopt_summary_v1.json"
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc.get("schema") == "weather_btrack_pipeline_hypo_fusionopt_summary_v1"
    assert doc.get("hypo_boundary_ack") is True
    fm = doc.get("fusion_optimizer_metrics") or {}
    assert "best_fusion_weight_myeongri" in fm
    bm = doc.get("brier_eval_metrics") or {}
    assert bm.get("n_evaluated") == 360


def test_committed_triplet_registry_ece_by_domain_tag_smoke() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(_COMMITTED_REGISTRY),
            "--stdout-only",
            "--no-rows",
            "--ece-bins",
            "10",
            "--ece-min-per-tag",
            "1",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    by_tag = doc.get("metrics", {}).get("ece_binary_by_domain_tag") or {}
    assert "lens_myeongri" in by_tag and "lens_sasang" in by_tag and "lens_fusion_v1" in by_tag


def test_committed_triplet_registry_brier_smoke() -> None:
    assert _COMMITTED_REGISTRY.is_file()
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(_COMMITTED_REGISTRY),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc.get("schema") == "general_prophecy_brier_eval_v1"
    n = doc.get("metrics", {}).get("n_evaluated")
    assert n == 6
    by_tag = doc.get("metrics", {}).get("by_domain_tag", {})
    assert "lens_myeongri" in by_tag and by_tag["lens_myeongri"].get("n_evaluated") == 2
    assert "lens_sasang" in by_tag and by_tag["lens_sasang"].get("n_evaluated") == 2
    assert "lens_fusion_v1" in by_tag and by_tag["lens_fusion_v1"].get("n_evaluated") == 2
    assert "weather_calibration_v1" in by_tag and by_tag["weather_calibration_v1"].get("n_evaluated") == 6


def test_csv_to_weather_gt_jsonl_subprocess(tmp_path) -> None:
    out = tmp_path / "gt.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_CSV),
            "-i",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2


def test_triplet_registry_builder_subprocess(tmp_path) -> None:
    gt = _ROOT / "tests" / "fixtures" / "weather_ground_truth_rows_v1.sample.jsonl"
    reg = tmp_path / "triplet.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_TRIPLET),
            "--input-jsonl",
            str(gt),
            "--output",
            str(reg),
            "--stub-probability",
            "0.5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert data.get("schema") == "general_prophecy_registry_v1"
    assert len(data.get("questions", [])) == 6


def test_run_weather_chain_auto_forecasts_sidecar_subprocess(tmp_path) -> None:
    out = tmp_path / "reg_auto.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--auto-forecasts-sidecar",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "auto sidecar" in r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    qs = data.get("questions") or []
    assert len(qs) == 6
    p0 = (qs[0].get("forecasts") or [{}])[0].get("probability_0_1")
    assert isinstance(p0, (int, float)) and abs(float(p0) - 0.5) > 1e-6


def test_run_weather_chain_auto_and_explicit_forecasts_conflict(tmp_path) -> None:
    out = tmp_path / "reg_x.json"
    fake_sidecar = tmp_path / "fc.jsonl"
    fake_sidecar.write_text('{"x":1}\n', encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--auto-forecasts-sidecar",
            "--forecasts-jsonl",
            str(fake_sidecar),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 2
    assert "only one of" in r.stderr.lower() or "only one of" in r.stdout.lower()


def test_run_weather_gt_to_prophecy_triplet_chain_subprocess(tmp_path) -> None:
    assert _CHAIN.is_file()
    out = tmp_path / "registry.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--source-dataset-name",
            "pytest_chain",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "(validated)" in r.stderr
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data.get("questions", [])) == 6
    jl = out.with_name(out.stem + "_gt_labels.jsonl")
    assert jl.is_file()


def test_run_weather_chain_skip_validate_no_validated_marker(tmp_path) -> None:
    out = tmp_path / "registry_skip.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--skip-validate-jsonl",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "(validated)" not in r.stderr


def test_validate_weather_ground_truth_jsonl_synthetic_120() -> None:
    assert _SYNTHETIC_JSONL.is_file()
    r = subprocess.run(
        [sys.executable, str(_VALIDATE), "-i", str(_SYNTHETIC_JSONL)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert '"n_hard_errors": 0' in r.stderr


def test_csv_to_weather_gt_jsonl_max_rows_subprocess(tmp_path) -> None:
    """--max-rows limits emitted lines from a larger CSV."""
    src = _ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_input.csv"
    assert src.is_file()
    out = tmp_path / "subset.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_CSV),
            "-i",
            str(src),
            "-o",
            str(out),
            "--strict-schema",
            "--max-rows",
            "5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5


def test_run_weather_gt_chain_help_has_examples_epilog() -> None:
    r = subprocess.run(
        [sys.executable, str(_CHAIN), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "Examples" in r.stdout and "Kaggle-style" in r.stdout
    assert "--auto-columns-csv" in r.stdout
    assert "--fusion-weight-myeongri" in r.stdout
    assert "--fusion-search-json" in r.stdout
    assert "optimize_weather_lens_fusion_weights_v1" in r.stdout


def test_run_weather_btrack_hypo_fusionopt_to_artifacts_help() -> None:
    r = subprocess.run(
        [sys.executable, str(_BTRACK_ARTIFACT_RUNNER), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "HYPO" in r.stdout or "hypo" in r.stdout.lower()


def test_run_weather_btrack_external_forecasts_to_artifacts_help() -> None:
    r = subprocess.run(
        [sys.executable, str(_BTRACK_EXTERNAL_RUNNER), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "forecasts-jsonl" in r.stdout
    assert "run-label" in r.stdout


def test_run_weather_btrack_external_real_week_chain_ps1_exists() -> None:
    assert _BTRACK_EXTERNAL_REAL_WEEK_PS1.is_file()


def test_run_weather_btrack_external_real_week_full_gate_ps1_exists() -> None:
    assert _BTRACK_EXTERNAL_REAL_WEEK_FULL_GATE_PS1.is_file()


def test_run_weather_synthetic_120d_chain_and_brier_py_help() -> None:
    r = subprocess.run(
        [sys.executable, str(_SYNTH120_RUNNER), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "--stub-only" in r.stdout
    assert "--max-rows" in r.stdout and "--date-col" in r.stdout
    assert "--auto-columns-csv" in r.stdout
    assert "--forecasts-jsonl" in r.stdout
    assert "external_lens_hypo" in r.stdout or "HYPO external" in r.stdout
    assert "--ece-bins" in r.stdout
    assert "--ece-min-per-tag" in r.stdout
    assert "--fusion-weight-myeongri" in r.stdout
    assert "--fusion-search-json" in r.stdout
    assert "Examples" in r.stdout


def test_run_weather_synthetic_runner_stub_and_forecasts_jsonl_conflict() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_SYNTH120_RUNNER),
            "--stub-only",
            "--forecasts-jsonl",
            str(_ROOT / "tests" / "fixtures" / "weather_synthetic_120d_forecasts_sidecar_v1.jsonl"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 2
    assert "only one of" in r.stderr.lower()


def test_run_weather_synthetic_120d_chain_and_brier_forecasts_jsonl_two_rows(tmp_path) -> None:
    fx = _ROOT / "tests" / "fixtures" / "weather_synthetic_120d_forecasts_sidecar_v1.jsonl"
    two = tmp_path / "fc2.jsonl"
    lines = [ln for ln in fx.read_text(encoding="utf-8").splitlines() if ln.strip()][:2]
    two.write_text("\n".join(lines) + "\n", encoding="utf-8")
    reg = tmp_path / "r.json"
    br = tmp_path / "b.json"
    src = _ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_input.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_SYNTH120_RUNNER),
            "--csv",
            str(src),
            "--registry-json",
            str(reg),
            "--brier-out",
            str(br),
            "--max-rows",
            "2",
            "--forecasts-jsonl",
            str(two),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(reg.read_text(encoding="utf-8"))
    assert len(doc.get("questions") or []) == 6
    ev = json.loads(br.read_text(encoding="utf-8"))
    assert ev.get("metrics", {}).get("n_evaluated") == 6


def test_run_weather_synthetic_120d_chain_and_brier_max_rows_five(tmp_path) -> None:
    reg = tmp_path / "r.json"
    br = tmp_path / "b.json"
    src = _ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_input.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_SYNTH120_RUNNER),
            "--csv",
            str(src),
            "--registry-json",
            str(reg),
            "--brier-out",
            str(br),
            "--max-rows",
            "5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(reg.read_text(encoding="utf-8"))
    assert len(doc.get("questions") or []) == 15
    ev = json.loads(br.read_text(encoding="utf-8"))
    assert ev.get("metrics", {}).get("n_evaluated") == 15


def test_run_weather_synthetic_120d_chain_forecasts_jsonl_hypo_n360(tmp_path) -> None:
    """120일 합성 CSV + HYPO 외부 JSONL(120행) -> 레지스트리 360문항 + Brier n=360."""
    assert _EXTERNAL_120_HYPO_JSONL.is_file()
    reg = tmp_path / "reg_ext360.json"
    br = tmp_path / "b_ext360.json"
    src = _ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_input.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_SYNTH120_RUNNER),
            "--csv",
            str(src),
            "--registry-json",
            str(reg),
            "--brier-out",
            str(br),
            "--forecasts-jsonl",
            str(_EXTERNAL_120_HYPO_JSONL),
            "--ece-bins",
            "10",
            "--ece-min-per-tag",
            "5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(reg.read_text(encoding="utf-8"))
    assert len(doc.get("questions") or []) == 360
    ev = json.loads(br.read_text(encoding="utf-8"))
    assert ev.get("metrics", {}).get("n_evaluated") == 360


def test_run_weather_btrack_external_forecasts_to_artifacts_minimal(tmp_path) -> None:
    out_summary = tmp_path / "weather_btrack_pipeline_external_minimal_test_summary.json"
    out_cmp = tmp_path / "weather_btrack_summary_comparison_hypo_vs_external_minimal_test.json"
    baseline = _ROOT / "docs" / "final" / "artifacts" / "weather_btrack_pipeline_hypo_fusionopt_summary_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_BTRACK_EXTERNAL_RUNNER),
            "--csv",
            str(_MINIMAL_CSV),
            "--forecasts-jsonl",
            str(_EXTERNAL_FORECASTS_JSONL),
            "--run-label",
            "external_minimal_test",
            "--strict-schema-csv",
            "--artifacts-dir",
            str(tmp_path),
            "--out-dir",
            str(tmp_path),
            "--baseline-summary",
            str(baseline),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_summary.is_file()
    doc = json.loads(out_summary.read_text(encoding="utf-8"))
    assert doc.get("schema") == "weather_btrack_pipeline_external_summary_v1"
    assert doc.get("brier_eval_metrics", {}).get("n_evaluated") == 6
    assert out_cmp.is_file()


def test_weather_gt_jsonl_to_forecasts_sidecar_subprocess(tmp_path) -> None:
    out = tmp_path / "fc.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_SIDECAR),
            "-i",
            str(_SAMPLE_GT_JSONL),
            "-o",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert "p_myeongri" in first and "p_sasang" in first


def test_weather_csv_sniff_json_minimal_fixture() -> None:
    r = subprocess.run(
        [sys.executable, str(_SNIFF), "-i", str(_MINIMAL_CSV), "--json"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["date_col"] == "date"
    assert doc["precip_col"] == "precip_mm"
    assert doc["date_format"] == "%Y-%m-%d"
    assert doc["encoding"].startswith("utf-8")


def test_weather_csv_sniff_json_kaggle_style_headers() -> None:
    assert _KAGGLE_SNIFF_CSV.is_file()
    r = subprocess.run(
        [sys.executable, str(_SNIFF), "-i", str(_KAGGLE_SNIFF_CSV), "--json"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["date_col"] == "DATE"
    assert doc["precip_col"] == "RR"
    assert doc["date_format"] == "%Y-%m-%d"


def test_csv_to_weather_gt_jsonl_auto_columns_subprocess(tmp_path) -> None:
    out = tmp_path / "gt_auto.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_CSV),
            "-i",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--auto-columns",
            "--strict-schema",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "weather_csv_sniff:" in r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2


def test_run_weather_chain_auto_columns_csv_kaggle_fixture(tmp_path) -> None:
    out = tmp_path / "reg_auto_kaggle.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_KAGGLE_SNIFF_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--auto-columns-csv",
            "--auto-forecasts-sidecar",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "weather_csv_sniff:" in r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data.get("questions", [])) == 6


def test_run_weather_chain_fusion_search_json_overrides_weight(tmp_path) -> None:
    """--fusion-search-json 이 metrics.best_fusion_weight_myeongri=1.0 이면 명리와 융합 확률 동일."""
    search = tmp_path / "fusion_search.json"
    search.write_text(
        json.dumps(
            {
                "schema": "weather_lens_fusion_weight_search_v1",
                "metrics": {"best_fusion_weight_myeongri": 1.0},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "reg_fusion_search.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--forecasts-jsonl",
            str(_EXTERNAL_FORECASTS_JSONL),
            "--fusion-search-json",
            str(search),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "fusion_weight_myeongri=1.0" in r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    by_id = {q["question_id"]: q for q in (data.get("questions") or [])}
    qm = by_id["btrack.weather_hist.seoul108.20150715.lens_myeongri"]
    qf = by_id["btrack.weather_hist.seoul108.20150715.lens_fusion_v1"]
    assert qm["forecasts"][0]["probability_0_1"] == qf["forecasts"][0]["probability_0_1"]


def test_run_weather_chain_fusion_weight_myeongri_one_follows_myeongri_lens(tmp_path) -> None:
    """--fusion-weight-myeongri 1.0 이면 융합 확률이 명리 렌즈와 동일."""
    out = tmp_path / "reg_fusion_w1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--forecasts-jsonl",
            str(_EXTERNAL_FORECASTS_JSONL),
            "--fusion-weight-myeongri",
            "1.0",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    by_id = {q["question_id"]: q for q in (data.get("questions") or [])}
    qm = by_id["btrack.weather_hist.seoul108.20150715.lens_myeongri"]
    qf = by_id["btrack.weather_hist.seoul108.20150715.lens_fusion_v1"]
    assert qm["forecasts"][0]["probability_0_1"] == qf["forecasts"][0]["probability_0_1"]


def test_optimize_weather_lens_fusion_weights_subprocess(tmp_path) -> None:
    """GT 120d + HYPO forecasts: 최적화 JSON 스키마 및 best W 존재."""
    out = tmp_path / "fusion_search.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_OPTIM_FUSION),
            "-g",
            str(_SYNTHETIC_JSONL),
            "-f",
            str(_EXTERNAL_120_HYPO_JSONL),
            "-o",
            str(out),
            "--grid-points",
            "51",
            "--ece-bins",
            "10",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "weather_lens_fusion_weight_search_v1"
    m = doc.get("metrics") or {}
    assert 0.0 <= float(m["best_fusion_weight_myeongri"]) <= 1.0
    assert "ece_binary_fusion_at_best_w" in m


def test_eval_general_prophecy_brier_writes_file_no_print_output_path(tmp_path) -> None:
    br = tmp_path / "m.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(_COMMITTED_REGISTRY),
            "-o",
            str(br),
            "--no-rows",
            "--no-print-output-path",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
    assert br.is_file()
    assert json.loads(br.read_text(encoding="utf-8")).get("schema") == "general_prophecy_brier_eval_v1"


def test_run_weather_chain_forecasts_jsonl_external_lens_probabilities(tmp_path) -> None:
    """외부 p_myeongri/p_sasang JSONL이 레지스트리 확률에 그대로 반영되는지 (합성 사이드카 아님)."""
    assert _EXTERNAL_FORECASTS_JSONL.is_file()
    out = tmp_path / "reg_external_lens.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(_MINIMAL_CSV),
            "-o",
            str(out),
            "--strict-schema-csv",
            "--forecasts-jsonl",
            str(_EXTERNAL_FORECASTS_JSONL),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "auto sidecar" not in r.stderr.lower()
    data = json.loads(out.read_text(encoding="utf-8"))
    qs = data.get("questions") or []
    assert len(qs) == 6
    by_id = {q["question_id"]: q for q in qs}
    qm = by_id["btrack.weather_hist.seoul108.20150715.lens_myeongri"]
    assert abs(float(qm["forecasts"][0]["probability_0_1"]) - 0.62) < 1e-9
    qsas = by_id["btrack.weather_hist.seoul108.20150715.lens_sasang"]
    assert abs(float(qsas["forecasts"][0]["probability_0_1"]) - 0.38) < 1e-9
    qf = by_id["btrack.weather_hist.seoul108.20150715.lens_fusion_v1"]
    assert abs(float(qf["forecasts"][0]["probability_0_1"]) - 0.5) < 1e-9
    qm2 = by_id["btrack.weather_hist.seoul108.20150716.lens_myeongri"]
    assert abs(float(qm2["forecasts"][0]["probability_0_1"]) - 0.25) < 1e-9
    qsas2 = by_id["btrack.weather_hist.seoul108.20150716.lens_sasang"]
    assert abs(float(qsas2["forecasts"][0]["probability_0_1"]) - 0.71) < 1e-9
    qf2 = by_id["btrack.weather_hist.seoul108.20150716.lens_fusion_v1"]
    assert abs(float(qf2["forecasts"][0]["probability_0_1"]) - 0.48) < 1e-9


def test_weather_csv_sniff_cp949_korean_headers(tmp_path) -> None:
    p = tmp_path / "cp949_weather.csv"
    p.write_bytes("날짜,강수량\n2015-07-15,3.5\n".encode("cp949"))
    r = subprocess.run(
        [sys.executable, str(_SNIFF), "-i", str(p), "--json"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["encoding"] == "cp949"
    assert doc["date_col"] == "날짜"
    assert doc["precip_col"] == "강수량"


def test_run_weather_chain_cp949_korean_csv_auto_columns_full(tmp_path) -> None:
    """CP949 + 한글 헤더: 스니프 → CSV → 체인 → 융합 forecasts (KMA 유사)."""
    p = tmp_path / "cp949_kr.csv"
    p.write_bytes(
        "날짜,강수량\n2015-07-15,12.4\n2015-07-16,0.0\n".encode("cp949"),
    )
    reg = tmp_path / "reg_cp949.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "-c",
            str(p),
            "-o",
            str(reg),
            "--strict-schema-csv",
            "--auto-columns-csv",
            "--auto-forecasts-sidecar",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "encoding=cp949" in r.stderr
    data = json.loads(reg.read_text(encoding="utf-8"))
    qs = data.get("questions") or []
    assert len(qs) == 6
    fusion = [q for q in qs if "lens_fusion_v1" in (q.get("domain_tags") or [])]
    assert len(fusion) == 2
    for q in fusion:
        fc = (q.get("forecasts") or [{}])[0]
        assert isinstance(fc.get("probability_0_1"), (int, float))
        assert fc.get("brier_ready") is True


def test_validate_forecasts_jsonl_against_gt_ok_external_minimal() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_VALIDATE_FC),
            "-g",
            str(_SAMPLE_GT_JSONL),
            "-f",
            str(_EXTERNAL_FORECASTS_JSONL),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stderr


def test_validate_forecasts_jsonl_against_gt_fails_missing_row(tmp_path) -> None:
    bad = tmp_path / "one_row.jsonl"
    bad.write_text(
        '{"observation_date_local": "2015-07-15", "station_or_region_id": "seoul_asos_108", '
        '"p_myeongri": 0.5, "p_sasang": 0.5}\n',
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(_VALIDATE_FC),
            "-g",
            str(_SAMPLE_GT_JSONL),
            "-f",
            str(bad),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 1
    assert "missing" in r.stderr.lower()


def test_emit_forecasts_template_then_validate_ok(tmp_path) -> None:
    out = tmp_path / "fc.jsonl"
    r1 = subprocess.run(
        [sys.executable, str(_EMIT_FC), "-i", str(_SAMPLE_GT_JSONL), "-o", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r1.returncode == 0, r1.stderr
    r2 = subprocess.run(
        [sys.executable, str(_VALIDATE_FC), "-g", str(_SAMPLE_GT_JSONL), "-f", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r2.returncode == 0, r2.stderr


def test_generate_general_prophecy_dry_run_committed_triplet() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "-i",
            str(_COMMITTED_REGISTRY),
            "--dry-run",
            "--no-default-merge",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().split()[-1] == "6"
