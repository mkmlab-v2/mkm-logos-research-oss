# @MKM12-METADATA
# Type: Test
# Purpose: B-track theory→gp orchestrator v0 smoke (experimental, no network).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PKG = _ROOT / "scripts" / "experimental" / "btrack_theory_to_gp_orchestrator_v0"
_RUN = _PKG / "run_orchestrator_v0.py"


@pytest.fixture
def pack_and_templates() -> tuple[dict, dict]:
    pack = json.loads((_PKG / "packs" / "ai_sox_logos_v0.json").read_text(encoding="utf-8"))
    templates = json.loads((_PKG / "proposition_templates_v0.json").read_text(encoding="utf-8"))
    return pack, templates


def test_build_registry_draft_validates_against_gp_schema(pack_and_templates: tuple[dict, dict]) -> None:
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.run_orchestrator_v0 import (
        build_registry_draft,
        validate_gp_registry,
    )

    pack, templates = pack_and_templates
    draft = build_registry_draft(pack, templates, issued_at_utc="2026-06-04T12:00:00Z")
    validate_gp_registry(draft)
    assert len(draft["questions"]) == 3
    ids = {q["question_id"] for q in draft["questions"]}
    assert "gp_2026_logos_sox_new_high_before_0930" in ids


def test_orchestrator_cli_draft_only(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    draft = tmp_path / "draft.json"
    sox = _ROOT / "research" / "market_data" / "sox_daily_external_yf.csv"
    if not sox.is_file():
        pytest.skip("SOX CSV missing; run fetch_sox_yfinance_csv.py")

    r = subprocess.run(
        [
            sys.executable,
            str(_RUN),
            "--draft-out",
            str(draft),
            "--audit-json",
            str(audit),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["ok"] is True
    assert payload["decision"] == "OK_DRAFT_ONLY"
    doc = json.loads(draft.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_registry_v1"
    assert len(doc["questions"]) == 3


def test_eval_sox_functions() -> None:
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.resolve_sox_gp_v1 import evaluate_all

    csv_path = _ROOT / "research" / "market_data" / "sox_daily_external_yf.csv"
    if not csv_path.is_file():
        pytest.skip("SOX CSV missing")

    body = evaluate_all(csv_path)
    assert body["ok"] is True
    for qid in (
        "gp_2026_logos_sox_new_high_before_0930",
        "gp_2026_logos_sox_daily_drop_ge_5pct_q3",
        "gp_2026_logos_sox_close_below_ref_minus_10pct_by_0930",
    ):
        assert qid in body["evaluations"]
        assert body["evaluations"][qid].get("ok") is True
        assert body["evaluations"][qid]["outcome_binary"] in (True, False)


def test_nvda_pack_builds_one_question() -> None:
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.run_orchestrator_v0 import (
        _load_json,
        build_registry_draft,
        validate_gp_registry,
    )

    pkg = _ROOT / "scripts/experimental/btrack_theory_to_gp_orchestrator_v0"
    pack = _load_json(pkg / "packs/ai_nvda_qqq_logos_v0.json")
    templates = _load_json(pkg / "proposition_templates_v0.json")
    draft = build_registry_draft(pack, templates, issued_at_utc="2026-06-04T12:00:00Z")
    validate_gp_registry(draft)
    assert len(draft["questions"]) == 1
    assert draft["questions"][0]["question_id"] == "gp_2026_logos_nvda_daily_drop_ge_7pct_q3"


def test_orchestrator_merge_dry_run(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    draft = tmp_path / "draft.json"
    sox = _ROOT / "research" / "market_data" / "sox_daily_external_yf.csv"
    if not sox.is_file():
        pytest.skip("SOX CSV missing")

    r = subprocess.run(
        [
            sys.executable,
            str(_RUN),
            "--draft-out",
            str(draft),
            "--audit-json",
            str(audit),
            "--merge-registry",
            "--merge-dry-run",
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    audit_doc = json.loads(audit.read_text(encoding="utf-8"))
    assert audit_doc["decision"] == "OK_MERGE_DRY_RUN"


def test_eval_nvda_and_qqq_functions() -> None:
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.resolve_nvda_gp_v1 import evaluate_all as eval_nvda
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.resolve_qqq_gp_v1 import evaluate_all as eval_qqq

    nvda_csv = _ROOT / "research/market_data/nvda_daily_external_yf.csv"
    qqq_csv = _ROOT / "research/market_data/qqq_daily_external_yf.csv"
    if not nvda_csv.is_file() or not qqq_csv.is_file():
        pytest.skip("NVDA/QQQ CSV missing")

    nvda_body = eval_nvda(nvda_csv)
    assert nvda_body["ok"] is True
    ev = nvda_body["evaluations"]["gp_2026_logos_nvda_daily_drop_ge_7pct_q3"]
    assert ev.get("ok") is True
    assert ev["outcome_binary"] in (True, False)

    qqq_body = eval_qqq(qqq_csv)
    assert qqq_body["ok"] is True
    ev2 = qqq_body["evaluations"]["gp_2026_logos_qqq_new_high_before_0930"]
    assert ev2.get("ok") is True
    assert ev2["outcome_binary"] in (True, False)


def test_eval_june_functions() -> None:
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.resolve_logos_june_gp_v1 import evaluate_all

    body = evaluate_all()
    assert body["ok"] is True
    for qid in (
        "gp_2026_logos_kospi_close_below_8500_by_0630",
        "gp_2026_logos_nasdaq_daily_drop_ge_3pct_june",
        "gp_2026_logos_brent_spot_ge_95_before_0701",
        "gp_2026_logos_vix_close_ge_25_june",
    ):
        ev = body["evaluations"][qid]
        assert ev.get("ok") is True
        assert ev["outcome_binary"] in (True, False)
        assert ev.get("deadline_passed") is False


def test_unified_gp_preview_cli() -> None:
    sox = _ROOT / "research/market_data/sox_daily_external_yf.csv"
    if not sox.is_file():
        pytest.skip("SOX CSV missing")
    batch = _PKG / "run_logos_gp_resolve_preview_v1.py"
    r = subprocess.run(
        [sys.executable, str(batch)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = _ROOT / "reports/general_prophecy_logos_gp_monthly_preview_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("summaries", {}).get("june") is not None


def test_ai_equity_batch_preview_cli() -> None:
    sox = _ROOT / "research/market_data/sox_daily_external_yf.csv"
    if not sox.is_file():
        pytest.skip("SOX CSV missing")
    batch = _PKG / "run_logos_ai_equity_gp_resolve_preview_v1.py"
    r = subprocess.run(
        [sys.executable, str(batch)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(r.stdout.strip())
    assert payload["ok"] is True
