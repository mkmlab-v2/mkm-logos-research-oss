"""Logos inquiry report v1 — P0-1a schema freeze · S1-S5 · query contract."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_report_v1 import (  # noqa: E402
    SCHEMA,
    build_inquiry_report,
    load_freeze_lexicon_meta,
    load_sasang_regime_hint_b_track,
)


def test_inquiry_report_s1_s5_schema():
    payload = {
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "answer": "sample",
        "path": {"verse_refs": ["Job.1.21"], "steps": ["lemma_faith"], "node_ids": ["lemma_faith"]},
        "conflict_context": {"groups": []},
    }
    report = build_inquiry_report(payload, query="욥기 고난?", intake={"intake_gate": "PASS"})
    assert report["schema"] == SCHEMA
    assert report["tier"] == "standard"
    assert set(report["sections"].keys()) == {"S1", "S2", "S3", "S4", "S5"}
    assert report["sections"]["S1"]["section_id"] == "S1_citation_lock"
    assert "Job.1.21" in report["sections"]["S1"]["verse_refs"]
    assert report["sections"]["S2"]["lemma_edge_line_count"] is not None
    assert report["sections"]["S2"]["floor_pass"] is True
    assert report["sections"]["S5"]["sections_payload_sha256"]
    assert report["sections"]["S5"]["chain_exit_code"] == 0
    assert "무환각 0%" in report["governance"]["forbidden_claims"]


def test_s2_no_raw_dump_fields():
    meta = load_freeze_lexicon_meta()
    assert meta["lemma_edge_line_count"] >= 290_000
    payload = {"path": {"verse_refs": [], "steps": [], "node_ids": []}, "answer": "x"}
    report = build_inquiry_report(payload, query="test query long enough", freeze_meta=meta)
    s2 = report["sections"]["S2"]
    dumped = json.dumps(s2)
    assert "jsonl" not in dumped.lower() or "pointer" in dumped.lower()
    assert s2["lemma_edges_sha256"]
    assert "security_note_ko" in s2


def test_s2_manifest_sha256_runtime_pin():
    meta = load_freeze_lexicon_meta()
    assert meta.get("manifest_sha256")
    assert len(str(meta["manifest_sha256"])) == 64


def test_s3_sasang_regime_hint_optional():
    hint = load_sasang_regime_hint_b_track()
    payload = {
        "path": {"verse_refs": ["Gen.1.1"], "steps": [], "node_ids": []},
        "answer": "x",
        "conflict_context": {"groups": []},
    }
    report = build_inquiry_report(payload, query="창세기 1장 1절 의미는?", sasang_hint=hint)
    s3 = report["sections"]["S3"]
    if hint:
        assert s3.get("regime_hint_b_track", {}).get("token", "").startswith("Sasang_Regime:")
    s2 = report["sections"]["S2"]
    assert any(str(t).startswith("Gematria_Pin:") for t in s2.get("path_token_preview") or [])


def test_s4_allowlist_artifact():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_inquiry_s4_allowlist_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_freeze_chain_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_inquiry_report_schema_freeze_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    freeze = json.loads(
        (ROOT / "reports/logos_inquiry_report_schema_freeze_v1_latest.json").read_text(encoding="utf-8")
    )
    contract = json.loads(
        (ROOT / "docs/final/artifacts/logos_inquiry_query_contract_v1_latest.json").read_text(encoding="utf-8")
    )
    assert freeze["ok"] is True
    assert freeze["chain_exit_code"] == 0
    assert contract["endpoint"]["path"] == "/api/logos-research/query"
    assert contract["request"]["output_format"] == "studio_v1 | inquiry_report_v1 (default studio_v1)"
    sample = json.loads(
        (ROOT / "reports/logos_inquiry_report_sample_v1_latest.json").read_text(encoding="utf-8")
    )
    assert sample["output_format"] == "inquiry_report_v1"
