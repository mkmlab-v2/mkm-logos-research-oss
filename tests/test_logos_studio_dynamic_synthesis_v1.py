"""Logos Studio dynamic synthesis (Phase 2) tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_studio_conflict_retrieval_gate_v1.py"
SYNTH = ROOT / "scripts/synthesize_logos_studio_dynamic_answer_v1.py"
RETRIEVE = ROOT / "scripts/retrieve_logos_studio_conflict_context_v1.py"


def test_conflict_retrieval_gate_exit0():
    proc = subprocess.run([sys.executable, str(GATE)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True


def test_deterministic_synthesis_nephilim():
    rproc = subprocess.run(
        [sys.executable, str(RETRIEVE), "--query", "네피림", "--no-embedding"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    conflict = json.loads(rproc.stdout)
    payload = {
        "query": "네피림이 뭐야?",
        "preset_id": "bigset_topic_nephilim",
        "path": {
            "note_ko": "test path note",
            "verse_refs": ["Gen.6.4", "Gen.6.1"],
            "steps": [],
        },
        "conflict_context": conflict,
    }
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["synthesis_mode"] == "deterministic_conflict_parallel"
    assert doc["citation_valid"] is True
    assert "[HYPO]" in doc["answer_ko"]
    assert "학파 병렬" in doc["answer_ko"] or "Nephilim" in doc["answer_ko"]
    assert len(doc["answer_ko"]) > 200


def test_deterministic_synthesis_job_suffering():
    rproc = subprocess.run(
        [
            sys.executable,
            str(RETRIEVE),
            "--query",
            "욥의 고난의 이유는?",
            "--preset-id",
            "job_job_suffering_reason",
            "--no-embedding",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    conflict = json.loads(rproc.stdout)
    assert conflict["group_count"] >= 1
    payload = {
        "query": "욥의 고난의 이유는?",
        "preset_id": "job_job_suffering_reason",
        "path": {
            "note_ko": "Jer.30.7 → Job.42.10 경로",
            "verse_refs": ["Job.1.6", "Job.38.4", "Job.42.10", "Jer.30.7"],
            "steps": [],
        },
        "conflict_context": conflict,
    }
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["citation_valid"] is True
    assert "학파 병렬" in doc["answer_ko"]
    assert len(doc["answer_ko"]) > 200


def test_deterministic_synthesis_isaiah_youtube_spine():
    rproc = subprocess.run(
        [
            sys.executable,
            str(RETRIEVE),
            "--query",
            "이사야 66장 spine",
            "--preset-id",
            "isaiah_youtube_spine_v1",
            "--no-embedding",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    conflict = json.loads(rproc.stdout)
    assert conflict["group_count"] >= 1
    payload = {
        "query": "이사야서 16챕터 spine",
        "preset_id": "isaiah_youtube_spine_v1",
        "path": {
            "note_ko": "Isa.6.8 → Isa.40.1 → Isa.53.5 spine",
            "verse_refs": ["Isa.6.8", "Isa.40.1", "Isa.53.5", "Isa.65.17", "Rev.21.2"],
            "steps": [],
        },
        "conflict_context": conflict,
    }
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["synthesis_mode"] == "deterministic_conflict_parallel"
    assert doc["citation_valid"] is True
    assert "[HYPO]" in doc["answer_ko"]
    assert "학파 병렬" in doc["answer_ko"] or "Isaiah" in doc["answer_ko"] or "이사야" in doc["answer_ko"]
    assert len(doc["answer_ko"]) > 200


def test_llm_auto_falls_back_to_deterministic_without_ollama():
    rproc = subprocess.run(
        [
            sys.executable,
            str(RETRIEVE),
            "--query",
            "욥의 고난",
            "--preset-id",
            "job_job_suffering_reason",
            "--no-embedding",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    conflict = json.loads(rproc.stdout)
    payload = {
        "query": "욥의 고난의 이유는?",
        "preset_id": "job_job_suffering_reason",
        "path": {"note_ko": "test", "verse_refs": ["Job.1.6", "Job.38.4"], "steps": []},
        "conflict_context": conflict,
    }
    env = os.environ.copy()
    env["LOGOS_STUDIO_DYNAMIC_SYNTHESIS_LLM"] = "auto"
    env["LOGOS_STUDIO_SYNTHESIS_TIMEOUT_S"] = "3"
    env["OLLAMA_HOST"] = "http://127.0.0.1:1"
    env.pop("MKM_LOGOS_LLM_DISTILL_ENABLE", None)
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json", "--prefer-llm"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["synthesis_mode"] in {"deterministic_conflict_parallel", "llm_citation_lock"}
    assert doc.get("citation_valid") is True


def test_synthesis_skipped_without_conflict():
    payload = {"query": "욥기 고난", "path": {"verse_refs": []}, "conflict_context": None}
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    doc = json.loads(proc.stdout)
    assert doc["ok"] is False
