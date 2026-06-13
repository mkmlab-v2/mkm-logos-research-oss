from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_news_neutralizer_v1.py"
SCHEMA = ROOT / "docs/final/schemas/news_neutralizer_shadow_v1.schema.json"
FIXTURE = ROOT / "tests/fixtures/news_neutralizer_rss_fixture_v1.json"
DECK_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/mkmlife_news_observation_deck_v1.json"


def _run(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def test_script_exists() -> None:
    assert SCRIPT.is_file()


def test_dry_run_fixture_smoke(tmp_path: Path) -> None:
    out = tmp_path / "shadow.json"
    cp = _run("--dry-run", "--fixture", "--output-json", str(out), "--strict-lint")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "news_neutralizer_shadow_v1"
    assert doc["lane"] == "research_only"
    assert doc["auto_deck_publish"] is False
    assert doc["copy_lint"]["passed"] is True
    assert doc["provenance"]["mode"] == "fixture"


def test_shadow_schema_validation(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "shadow.json"
    cp = _run("--dry-run", "--fixture", "--output-json", str(out))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_clustering_merges_similar_fixture_titles(tmp_path: Path) -> None:
    out = tmp_path / "shadow.json"
    cp = _run("--dry-run", "--fixture", "--output-json", str(out), "--window-hours", "48")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ingest"]["items_in_window"] >= 4
    member_counts = [c["member_count"] for c in doc["clusters"]]
    assert any(n >= 2 for n in member_counts), member_counts


def test_banned_copy_lint_unit() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("news_neutralizer_mod", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lint_public_copy_v1 = mod.lint_public_copy_v1

    assert lint_public_copy_v1("This is a buy now signal for BTC") == ["investment_advice_en"]
    assert lint_public_copy_v1("매수 추천합니다") == ["trade_pick_ko"]
    assert lint_public_copy_v1("편향 제거 완료 100% 중립") == ["portal_claim_ko"]


def test_does_not_overwrite_public_deck(tmp_path: Path) -> None:
    if not DECK_PUBLIC.is_file():
        pytest.skip("public deck not present in workspace")
    before = DECK_PUBLIC.read_bytes()
    out = tmp_path / "shadow.json"
    cp = _run("--dry-run", "--fixture", "--output-json", str(out))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    after = DECK_PUBLIC.read_bytes()
    assert before == after


def test_synthesis_has_opinion_and_hypo_disclaimer(tmp_path: Path) -> None:
    out = tmp_path / "shadow.json"
    cp = _run("--dry-run", "--fixture", "--output-json", str(out))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    syn = json.loads(out.read_text(encoding="utf-8"))["synthesis"]
    assert "[OPINION]" in syn["our_view_opinion_ko"]
    assert "[HYPO]" in syn["disclaimer_ko"]
    assert "투자" in syn["disclaimer_ko"]
