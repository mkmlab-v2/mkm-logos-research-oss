# Keywords: system2, self_correction, fact_lock, gate, dry_run

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "docs" / "final" / "artifacts" / "fixtures"


def _import_gate():
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import (
        append_passed_log,
        run_gate,
        validate_draft,
        validate_report,
    )

    return run_gate, validate_draft, validate_report, append_passed_log


def test_validate_pass_fixture():
    _, validate_draft, _, _ = _import_gate()
    draft = (FIX / "mkm_system2_gate_draft_pass_v1.txt").read_text(encoding="utf-8")
    assert validate_draft(draft) == []


def test_validate_fail_hypo_leak_and_ghost_metric():
    _, validate_draft, _, _ = _import_gate()
    draft = (FIX / "mkm_system2_gate_draft_fail_v1.txt").read_text(encoding="utf-8")
    errs = validate_draft(draft)
    assert "hypo_leak_to_track_a_or_live" in errs
    assert any(e.startswith("ghost_metric:") for e in errs)


def test_run_gate_pass_dry_run():
    run_gate, _, validate_report, _ = _import_gate()
    draft = (FIX / "mkm_system2_gate_draft_pass_v1.txt").read_text(encoding="utf-8")
    doc = run_gate(draft, max_retries=2, dry_run=True, mission_log=None, central=None)
    validate_report(doc)
    assert doc["all_pass"] is True
    assert doc["dry_run"] is True
    assert doc["final_action"]["decision"] == "GO"


def test_run_gate_fail_after_retries():
    run_gate, _, validate_report, _ = _import_gate()
    draft = "[HYPO] only text without repair path for live GO 실매매 GO"
    doc = run_gate(draft, max_retries=0, dry_run=True, mission_log=None, central=None)
    validate_report(doc)
    assert doc["all_pass"] is False
    assert doc["final_action"]["decision"] == "HOLD"
    assert doc["retry_count"] == 0


def test_run_gate_repair_then_pass():
    run_gate, _, validate_report, _ = _import_gate()
    draft = "성경 렌즈가 하락을 예언했다. Field HOLD."
    doc = run_gate(draft, max_retries=2, dry_run=True, mission_log=None, central=None)
    validate_report(doc)
    assert doc["all_pass"] is True
    assert "[NON_GATING]" in doc["draft_final"]


def test_ghost_metric_allowed_in_field_context():
    _, validate_draft, _, _ = _import_gate()
    ctx = json.loads((FIX / "mkm_system2_gate_field_context_v1.json").read_text(encoding="utf-8"))
    draft = "Track A bench coverage=47.5% ( cited ). [NON_GATING] Logos note."
    assert validate_draft(draft, field_context=ctx) == []


def test_append_passed_log(tmp_path: Path):
    _, _, _, append_passed_log = _import_gate()
    log = tmp_path / "passed.jsonl"
    doc = {
        "dry_run": True,
        "draft_final": "ok",
        "sources": [],
    }
    append_passed_log(doc, log)
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["source_tag"] == "system2_gate_mvp_v1"


def test_cli_run_pass(tmp_path: Path):
    pytest.importorskip("jsonschema")
    draft = FIX / "mkm_system2_gate_draft_pass_v1.txt"
    out = tmp_path / "report.json"
    import subprocess
    import sys

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "mkm_system2_self_correction_gate_mvp_v1.py"),
            "run",
            "--draft-file",
            str(draft),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["all_pass"] is True


def test_post_pass_hooks_promotion_and_vertex(tmp_path: Path):
    run_gate, _, _, _ = _import_gate()
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import (
        apply_post_pass_hooks,
        build_memory_promotion_candidate,
    )

    draft = (FIX / "mkm_system2_gate_draft_pass_v1.txt").read_text(encoding="utf-8")
    doc = run_gate(draft, max_retries=2, dry_run=True, mission_log=None, central=None)
    gate_out = tmp_path / "gate.json"
    promo_out = tmp_path / "promo.json"
    staging = tmp_path / "vertex.jsonl"
    hooks = apply_post_pass_hooks(
        doc,
        gate_report_path=gate_out,
        vertex_staging_path=staging,
        promotion_out_path=promo_out,
    )
    assert hooks["applied"] is True
    assert promo_out.is_file()
    assert staging.read_text(encoding="utf-8").strip()
    promo = json.loads(promo_out.read_text(encoding="utf-8"))
    assert promo["eligible"] is True
    assert promo["human_sign_off_required"] is True


def test_meta_layer_fail_downgrades_gate(tmp_path: Path):
    run_gate, _, _, _ = _import_gate()
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import apply_post_pass_hooks

    draft = (FIX / "mkm_system2_gate_draft_pass_v1.txt").read_text(encoding="utf-8")
    doc = run_gate(draft, max_retries=2, dry_run=True, mission_log=None, central=None)
    missing = tmp_path / "missing_envelope.json"
    hooks = apply_post_pass_hooks(doc, gate_report_path=tmp_path / "g.json", meta_layer_json=missing)
    assert hooks["meta_layer"]["ok"] is False
    assert doc["all_pass"] is False


def test_meta_layer_validate_ok_with_fixture(tmp_path: Path):
    pytest.importorskip("jsonschema")
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import validate_meta_layer_envelope

    fixture = ROOT / "docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json"
    result = validate_meta_layer_envelope(fixture, append_log=False)
    assert result["ok"] is True


def test_gemini_repair_fallback_without_key():
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import attempt_gemini_repair

    draft = "성경 렌즈가 하락을 예언했다."
    errors = ["logos_gating_without_NON_GATING"]
    repaired, meta = attempt_gemini_repair(draft, errors, field_context=None)
    assert "[NON_GATING]" in repaired or "확인 필요" in repaired
    assert meta.get("fallback") or meta.get("ok") is not False


def test_human_signoff_validate_ok():
    pytest.importorskip("jsonschema")
    from scripts.mkm_system2_human_signoff_v1 import validate_signoff

    fixture = ROOT / "docs/final/artifacts/fixtures/mkm_system2_human_signoff_ack_v1.example.json"
    assert validate_signoff(fixture, required_scope="vertex_upload") == []
    assert validate_signoff(fixture, required_scope="checkpoint_apply") == []


def test_export_vertex_staging_pack(tmp_path: Path):
    staging = tmp_path / "staging.jsonl"
    row = {
        "schema": "mkm_system2_vertex_staging_row_v1",
        "recorded_at_utc": "2026-05-31T12:00:00Z",
        "source_tag": "system2_gate_mvp_v1",
        "text": "Field HOLD. [NON_GATING] note.",
        "human_sign_off_required": True,
    }
    staging.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    from scripts.export_system2_vertex_staging_pack_v1 import export_pack

    manifest = export_pack(staging, out_dir=tmp_path / "pack", limit=10)
    assert manifest["exported_count"] == 1


def test_invoke_vertex_upload_dry_plan(tmp_path: Path):
    pytest.importorskip("jsonschema")
    staging = tmp_path / "staging.jsonl"
    row = {
        "schema": "mkm_system2_vertex_staging_row_v1",
        "recorded_at_utc": "2026-05-31T12:00:00Z",
        "source_tag": "system2_gate_mvp_v1",
        "text": "Field HOLD.",
        "human_sign_off_required": True,
    }
    staging.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    signoff = ROOT / "docs/final/artifacts/fixtures/mkm_system2_human_signoff_ack_v1.example.json"
    from scripts.invoke_system2_vertex_staging_upload_v1 import run_invoke

    doc = run_invoke(
        signoff_json=signoff,
        apply_upload=False,
        project="mkm-lab-agi-2025",
        bucket="mkm-lab-agi-2025-vertex-ai-staging",
        staging_jsonl=staging,
    )
    assert doc["ok"] is True
    assert doc["apply_upload"] is False


def test_system2_gate_agent_search_profile(tmp_path: Path):
    from scripts.build_and_upload_agent_search_corpus_v1 import SYSTEM2_GATE_DIR, _system2_gate_corpus_entries

    SYSTEM2_GATE_DIR.mkdir(parents=True, exist_ok=True)
    sample = SYSTEM2_GATE_DIR / "sample_gate_row.md"
    sample.write_text("# sample\n", encoding="utf-8")
    try:
        entries = _system2_gate_corpus_entries()
        assert any(e["pdf_name"] == "sample_gate_row.pdf" for e in entries)
    finally:
        if sample.is_file():
            sample.unlink()


def test_invoke_with_agent_search_corpus_dry_run(tmp_path: Path):
    pytest.importorskip("jsonschema")
    staging = tmp_path / "staging.jsonl"
    row = {
        "schema": "mkm_system2_vertex_staging_row_v1",
        "recorded_at_utc": "2026-05-31T12:00:00Z",
        "source_tag": "system2_gate_mvp_v1",
        "text": "Field HOLD.",
        "human_sign_off_required": True,
    }
    staging.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    signoff = ROOT / "docs/final/artifacts/fixtures/mkm_system2_human_signoff_ack_v1.example.json"
    from scripts.invoke_system2_vertex_staging_upload_v1 import run_invoke

    doc = run_invoke(
        signoff_json=signoff,
        apply_upload=False,
        project="mkm-lab-agi-2025",
        bucket="mkm-lab-agi-2025-vertex-ai-staging",
        staging_jsonl=staging,
        agent_search_corpus_dry_run=True,
    )
    assert doc["ok"] is True
    assert doc.get("agent_search_corpus", {}).get("ok") is True


def test_gemini_smoke_skips_without_key(tmp_path: Path):
    import subprocess
    import sys

    out = tmp_path / "smoke.json"
    env = {k: v for k, v in __import__("os").environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_STUDIO_API_KEY")}
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_mkm_system2_gemini_repair_smoke_v1.py"), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("skipped") is True


def test_validate_live_promotion_language_blocked():
    _, validate_draft, _, _ = _import_gate()
    bad = "Track A 승격 및 실매매 GO 여부는 추후 결정."
    assert "live_promotion_language" in validate_draft(bad)
    safe = "Track A 승격은 확인 필요(Track A/실매매 자동 합선 금지)로 대체됨."
    assert "live_promotion_language" not in validate_draft(safe)


def test_ollama_repair_mock(monkeypatch):
    from scripts.mkm_system2_self_correction_gate_mvp_v1 import attempt_ollama_repair

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Field 관망. 확인 필요(Track A/실매매 자동 합선 금지)."}}]}
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    text, meta = attempt_ollama_repair("[HYPO] bad", ["ghost_metric:72%"])
    assert meta.get("ok") is True
    assert meta.get("engine") == "ollama"
    assert "확인 필요" in text


def test_ollama_smoke_skips_unreachable(tmp_path: Path):
    import os
    import subprocess
    import sys

    out = tmp_path / "ollama_smoke.json"
    env = {k: v for k, v in os.environ.items()}
    env["OLLAMA_HOST"] = "http://127.0.0.1:59999"
    env.pop("MKM_SYSTEM2_OLLAMA_BASE_URL", None)
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_mkm_system2_ollama_repair_smoke_v1.py"), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("skipped") is True


def test_chain_cli_pass(tmp_path: Path):
    import subprocess
    import sys

    draft = FIX / "mkm_system2_gate_draft_pass_v1.txt"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mkm_system2_self_correction_gate_chain_v1.py"),
            "--draft-file",
            str(draft),
            "--skip-pytest",
            "--chain-out-json",
            str(tmp_path / "chain.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cp.returncode == 0, cp.stderr
    chain = json.loads((tmp_path / "chain.json").read_text(encoding="utf-8"))
    assert chain["ok"] is True

