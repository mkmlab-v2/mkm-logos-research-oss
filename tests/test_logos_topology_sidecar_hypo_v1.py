"""Layer A topology sidecar ingest — external Deep Research isolation ([HYPO])."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/logos/topology_sidecar_job_suffering_hypo_v1.seed.json"
INGESTED = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
CHAIN = ROOT / "reports/logos_topology_sidecar_ingest_chain_v1_latest.json"


def test_topology_sidecar_seed_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_logos_topology_sidecar_hypo_v1.py",
            "--input",
            str(SEED),
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_topology_sidecar_ingest_chain_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_topology_sidecar_ingest_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert INGESTED.is_file()
    doc = json.loads(INGESTED.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_topology_sidecar_ingested_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert doc["materialize_canon"] is False
    topo = doc["topology"]
    assert topo["hypothesis_class"] == "HYPO"
    assert topo["intentional_causal_gap"]["why_question_assembled"] is False
    assert len(topo["reading_pack"]) >= 3
    pack1 = next((p for p in topo["reading_pack"] if p.get("pack_id") == "integrated_topology"), None)
    assert pack1 and pack1.get("deep_synthesis_md_path")
    assert (ROOT / pack1["deep_synthesis_md_path"]).is_file()
    pack2 = next((p for p in topo["reading_pack"] if p.get("pack_id") == "scope_reset_no_why"), None)
    assert pack2 and pack2.get("deep_synthesis_md_path")
    assert (ROOT / pack2["deep_synthesis_md_path"]).is_file()
    pack3 = next((p for p in topo["reading_pack"] if p.get("pack_id") == "literal_council_only"), None)
    assert pack3 and pack3.get("deep_synthesis_md_path")
    assert (ROOT / pack3["deep_synthesis_md_path"]).is_file()
    cross = doc["corpus_cross_check"]
    assert cross["refs_total"] >= 10
    assert CHAIN.is_file()
    chain = json.loads(CHAIN.read_text(encoding="utf-8"))
    assert chain["ok"] is True


def test_topology_sidecar_rejects_bad_send_gate(tmp_path: Path) -> None:
    bad = json.loads(SEED.read_text(encoding="utf-8"))
    bad["send_gate"] = "OPEN"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    from scripts.ingest_logos_topology_sidecar_hypo_v1 import validate_topology_sidecar

    errors, _ = validate_topology_sidecar(bad)
    assert any("send_gate" in e for e in errors)


def test_job_bridge_lemma_verify_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/verify_logos_job_bridge_lemma_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/logos_job_bridge_lemma_verify_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert all(row["corpus_present"] for row in doc["lemma_verification"])


def test_job_scope_reset_verify_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/verify_logos_job_scope_reset_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/logos_job_scope_reset_verify_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["anchor_verse"]["why_lemma_lamah_present"] is False
    assert all(row["corpus_present"] for row in doc["scope_lemma_verification"])


def test_job_literal_council_verify_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/verify_logos_job_literal_council_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/logos_job_literal_council_verify_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["anchor_ref"] == "Job.1.6"
    assert doc["council_verse"]["ha_satan_definite_article"] is True
    assert all(row["corpus_present"] for row in doc["council_verse"]["lemma_verification"])


def test_job_reading_pack_verify_chain_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_job_reading_pack_verify_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert len(doc["reading_pack_order"]) == 3
    for pack_id in doc["reading_pack_order"]:
        assert doc["steps"][pack_id]["ok"] is True
