"""KOSPI DART MD&A PoC gate tests (B-track sandbox)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts/ingest_dart_mda_section_v1.py"
SYNTH = ROOT / "scripts/synthesize_kospi_dart_mda_answer_v1.py"
GATE = ROOT / "scripts/check_kospi_dart_mda_poc_gate_v1.py"
CORPUS = ROOT / "docs/final/artifacts/kospi_dart_mda_corpus_v1_latest.json"
QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_poc_queries_v1.json"


def _run(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_ingest_fixture_exit0(tmp_path: Path) -> None:
    out = tmp_path / "corpus.json"
    proc = _run([sys.executable, str(INGEST), "--mode", "fixture", "--out", str(out)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_dart_mda_corpus_v1"
    assert doc["table_excluded_v1"] is True
    assert len(doc["paragraphs"]) >= 5
    assert doc["paragraphs"][0]["paragraph_id"] == "DART-MDNA-P001"


def test_synthesis_in_scope_citation_lock(tmp_path: Path) -> None:
    out = tmp_path / "corpus.json"
    _run([sys.executable, str(INGEST), "--mode", "fixture", "--out", str(out)])
    proc = _run(
        [
            sys.executable,
            str(SYNTH),
            "--query",
            "연구개발비 증가 이유",
            "--corpus",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["citation_valid"] is True
    assert "DART-MDNA-P" in doc["answer_ko"]
    assert "12%" in doc["answer_ko"]


def test_synthesis_scope_refusal(tmp_path: Path) -> None:
    out = tmp_path / "corpus.json"
    _run([sys.executable, str(INGEST), "--mode", "fixture", "--out", str(out)])
    proc = _run(
        [
            sys.executable,
            str(SYNTH),
            "--query",
            "다음 달 주가 전망은?",
            "--corpus",
            str(out),
        ]
    )
    doc = json.loads(proc.stdout)
    assert doc["ok"] is False
    assert doc["error_code"] == "SCOPE_VIOLATION_HONEST_REFUSAL"
    assert proc.returncode == 0


def test_gate_a_mechanical_exit0() -> None:
    proc = _run([sys.executable, str(GATE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    artifact = ROOT / "docs/final/artifacts/kospi_dart_mda_poc_latest.json"
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["ok"] is True
    ga = report["gate_a_mechanical"]
    assert ga["orphan_paragraph_ref_rate"] == 0.0
    assert ga["numeric_unverified_rate"] == 0.0
    assert ga["scope_refusal_rate"] == 1.0


def test_queries_fixture_has_16_items() -> None:
    doc = json.loads(QUERIES.read_text(encoding="utf-8"))
    assert len(doc["items"]) == 16
    assert sum(1 for it in doc["items"] if it["scope"] == "in") == 12
    assert sum(1 for it in doc["items"] if it["scope"] == "out") == 4


def test_ingest_dart_zip_fixture(tmp_path: Path) -> None:
    zip_path = ROOT / "tests/fixtures/dart_mda_document_v1.zip"
    assert zip_path.is_file(), "run py scripts/bootstrap_dart_mda_fixture_zip_v1.py"
    out = tmp_path / "corpus_zip.json"
    proc = _run(
        [
            sys.executable,
            str(INGEST),
            "--mode",
            "dart_zip",
            "--zip-file",
            str(zip_path),
            "--out",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ingest_mode"] == "dart_zip"
    assert doc["ingest_meta"]["parser_schema"] == "dart_document_zip_parse_v1"
    assert len(doc["paragraphs"]) >= 2
    assert "재무에 관한 사항" not in doc["paragraphs"][-1]["text_ko"]


def test_parse_dart_zip_mda_end_trim() -> None:
    proc = _run(
        [
            sys.executable,
            str(ROOT / "scripts/parse_dart_document_zip_v1.py"),
            "--zip-file",
            str(ROOT / "tests/fixtures/dart_mda_document_v1.zip"),
            "--mda-only",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    text = proc.stdout
    assert "12%" in text
    assert "재무에 관한 사항" not in text


def test_gate_b_timing_sheet_exit0() -> None:
    proc = _run([sys.executable, str(ROOT / "scripts/build_kospi_dart_mda_poc_human_timing_v1.py")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads((ROOT / "reports/kospi_dart_mda_poc_human_timing_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["status"] == "awaiting_commander_trials"
    assert len(doc["trials"]) == 3
    assert doc["target_savings_ratio_min"] == 0.20


def test_resolve_rcept_skips_without_key(monkeypatch) -> None:
    import scripts.resolve_dart_corp_mda_rcept_no_v1 as mod

    monkeypatch.setattr(mod, "dart_api_key", lambda: "")
    out = mod.resolve("00126380", bgn_de="20230101", end_de="20261231")
    assert out.get("skipped") is True


def test_resolve_prefers_annual_report() -> None:
    from scripts.resolve_dart_corp_mda_rcept_no_v1 import pick_latest_mda_report

    doc = {
        "status": "000",
        "list": [
            {"report_nm": "분기보고서 (2026.03)", "rcept_dt": "20260515", "rcept_no": "Q"},
            {"report_nm": "사업보고서 (2025.12)", "rcept_dt": "20250311", "rcept_no": "A"},
        ],
    }
    picked = pick_latest_mda_report(doc)
    assert picked is not None
    assert picked["rcept_no"] == "A"


def test_gate_b_timing_check_awaiting_exit0() -> None:
    proc = _run([sys.executable, str(ROOT / "scripts/check_kospi_dart_mda_poc_human_timing_v1.py")])
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_gate_b_timing_pass_when_filled(tmp_path: Path) -> None:
    sheet = json.loads((ROOT / "reports/kospi_dart_mda_poc_human_timing_v1_latest.json").read_text(encoding="utf-8"))
    for t in sheet["trials"]:
        t["manual_sec"] = 100.0
        t["poc_click_verify_sec"] = 70.0
    path = tmp_path / "timing.json"
    path.write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")
    proc = _run(
        [
            sys.executable,
            str(ROOT / "scripts/check_kospi_dart_mda_poc_human_timing_v1.py"),
            "--in",
            str(path),
        ]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


LIVE_QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_live_smoke_queries_v1.json"
LIVE_CORPUS = ROOT / "reports/kospi_dart_mda_corpus_live_v1_latest.json"


def test_live_smoke_queries_fixture_shape() -> None:
    doc = json.loads(LIVE_QUERIES.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_dart_mda_live_smoke_queries_v1"
    items = doc["items"]
    assert len(items) == 7
    assert sum(1 for it in items if it["expect"] == "in_mda") == 5
    assert sum(1 for it in items if it["expect"] == "honest_miss") == 2


def test_live_gate_on_samsung_corpus_when_present() -> None:
    if not LIVE_CORPUS.is_file():
        return
    proc = _run([sys.executable, str(ROOT / "scripts/check_kospi_dart_mda_live_gate_v1.py")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    artifact = ROOT / "reports/kospi_dart_mda_live_gate_v1_latest.json"
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["live_gate"]["gate_pass"] is True


def test_honest_miss_no_hallucination_on_live_corpus() -> None:
    if not LIVE_CORPUS.is_file():
        return
    from scripts.kospi_dart_mda_poc_lib_v1 import build_deterministic_answer

    corpus = json.loads(LIVE_CORPUS.read_text(encoding="utf-8"))
    for q in ("연구개발비", "배당"):
        ans = build_deterministic_answer(q, corpus)
        assert ans.get("ok") is False
        assert ans.get("error") == "no_paragraph_hit"


LIVE_CORPS = ROOT / "docs/final/fixtures/kospi_dart_mda_live_corps_v1.json"


def test_live_corps_fixture_shape() -> None:
    doc = json.loads(LIVE_CORPS.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_dart_mda_live_corps_v1"
    assert doc.get("gate_b_status") == "deferred"
    assert len(doc["items"]) == 3
    slugs = {it["slug"] for it in doc["items"]}
    assert slugs == {"samsung", "skhynix", "lgenergy"}


def test_multi_corp_live_when_api_available() -> None:
    from scripts.kospi_dart_mda_poc_env_v1 import dart_api_key

    if not dart_api_key():
        return
    proc = _run([sys.executable, str(ROOT / "scripts/run_kospi_dart_mda_poc_multi_corp_live_v1.py")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((ROOT / "reports/kospi_dart_mda_poc_multi_corp_live_v1_latest.json").read_text(encoding="utf-8"))
    assert report.get("multi_corp_pass") is True
    for corp in report.get("corps") or []:
        assert corp.get("ok") is True
