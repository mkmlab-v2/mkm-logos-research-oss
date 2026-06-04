from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments/nextgen_clean_slate_cpu_v1"
TOPOLOGY_SCHEMA = ROOT / "docs/final/schemas/nextgen_clean_slate_cpu_topology_v1.schema.json"


def _run_script(script: str, *extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(ROOT / script), *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_topology_schema_exists() -> None:
    assert TOPOLOGY_SCHEMA.is_file()


def test_build_topology() -> None:
    out = EXP / "topology_spec_v1_latest.json"
    proc = _run_script(
        "scripts/build_nextgen_clean_slate_cpu_topology_v1.py",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    assert doc["evaluation_ssot"]["golden40_compatible"] is False


def test_rtt_loopback() -> None:
    out = EXP / "results/_test_rtt_probe_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_clean_slate_cpu_rtt_probe_v1.py",
        "--mode",
        "loopback",
        "--rounds",
        "5",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["mode"] == "loopback"
    grid = doc["measurement"]["grid"]
    assert len(grid) >= 1
    assert grid[0]["rtt_ms"]["p50"] is not None


def test_p0_microbench() -> None:
    out = EXP / "results/_test_p0_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_clean_slate_cpu_p0_microbench_v1.py",
        "--block-count",
        "8",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["results"]["throughput_mb_s"] > 0


def test_ng40_lexicon_ablation_quick() -> None:
    out = EXP / "results/_test_ng40_lexicon_ablation_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_latent_indexer_eval_ng40_lexicon_ablation_v1.py",
        "--quick",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc["arms"]) == 2
    assert "lexicon_on_minus_off_at_best_caps" in doc["attribution"]


def test_ng40_cap_sweep_fast() -> None:
    out = EXP / "results/_test_ng40_cap_sweep_v1.json"
    best = EXP / "results/_test_ng40_cap_sweep_best_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_latent_indexer_eval_ng40_cap_sweep_v1.py",
        "--preset",
        "fast",
        "--out-json",
        str(out),
        "--best-out-json",
        str(best),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["combo_count"] >= 1
    assert doc["rows"]
    assert best.is_file()


def test_ng40_latent_poc_sweep() -> None:
    out = EXP / "results/_test_ng40_poc_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_latent_indexer_poc_ng40_v1.py",
        "--sweep",
        "0.44",
        "0.48",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["implementation_phase"] == "p2_latent_salience_poc_v1"
    assert doc["aggregate"]["case_count"] >= 40


def test_ng40_latent_stub_shadow() -> None:
    out = EXP / "results/_test_ng40_shadow_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_latent_indexer_stub_ng40_shadow_v1.py",
        "--out-json",
        str(out),
        "--keep-percent",
        "82",
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["golden40_compatible"] is True
    assert doc["aggregate"]["case_count"] >= 40
    assert "beat_check" in doc


def test_ng40_poc_eval_hybrid_bench() -> None:
    out = EXP / "results/_test_poc_eval_hybrid_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_latent_poc_eval_hybrid_bench_v1.py",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "nextgen_latent_poc_eval_hybrid_v1"
    parallel = doc["eval_lane"]["beat_check_vs_parallel_bench"]
    assert parallel["beat_frozen"] is True, parallel
    active = doc["eval_lane"]["beat_check_vs_active_ssot"]
    assert active["beat_frozen"] is False
    assert float(active["delta_saving_pp"]) > 0
    assert doc["oracle_jaccard_upper_bound"]["aggregate"]["case_count"] >= 40


def test_p1_shard_loopback() -> None:
    out = EXP / "results/_test_p1_v1.json"
    proc = _run_script(
        "scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py",
        "--mode",
        "loopback",
        "--rounds",
        "5",
        "--out-json",
        str(out),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["measurement"]["elapsed_ms"]["p50"] is not None


def test_sandbox_chain_execute() -> None:
    import scripts.run_nextgen_clean_slate_cpu_sandbox_chain_v1 as mod

    doc = mod.build_plan(execute=True, aux_host=None, aux_ip=None)
    assert doc["nextgen_arm_status"] == "partial_poc"
    assert all(s["status"] == "ok" for s in doc["steps"]), doc["steps"]
    baseline_path = EXP / "results/nextgen_neural_baseline_v1_latest.json"
    assert baseline_path.is_file()
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert baseline["schema"] == "nextgen_neural_baseline_v1"
    assert baseline["golden40_compatible"] is False


def test_topology_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(TOPOLOGY_SCHEMA.read_text(encoding="utf-8"))
    charter = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
    if not charter.is_file():
        _run_script("scripts/build_btrack_nextgen_indexer_charter_v1.py")
    topo = EXP / "topology_spec_v1_latest.json"
    if not topo.is_file():
        _run_script(
            "scripts/build_nextgen_clean_slate_cpu_topology_v1.py",
            "--out-json",
            str(topo),
        )
    doc = json.loads(topo.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
