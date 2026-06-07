"""Smoke tests for logos chronology era blind eval (non-synthetic gold)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"
GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"


def test_era_blind_eval_runs_on_gold_fixture(tmp_path: Path) -> None:
    if not GOLD.is_file() or not CHRONO.is_file():
        return
    out = tmp_path / "blind_eval.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(GOLD),
            "--chronology-json",
            str(CHRONO),
            "--output-json",
            str(out),
            "--tag-mode",
            "gold_tags",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_era_blind_eval_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    assert doc["policy"]["non_gating"] is True
    assert doc["summary"]["n_non_synthetic"] >= 40
    assert doc["summary"]["hit_at_1_strict"] is not None
    assert "label_guided_seed" in (doc["inputs"].get("excluded_source_ids") or [])


def test_era_blind_eval_text_mode_smoke(tmp_path: Path) -> None:
    if not GOLD.is_file() or not CHRONO.is_file():
        return
    out = tmp_path / "blind_text.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(GOLD),
            "--chronology-json",
            str(CHRONO),
            "--output-json",
            str(out),
            "--tag-mode",
            "text_blind",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["tag_mode"] == "text_blind"


def test_hardset_v2_with_operator_proxy_overrides_non_self_match(tmp_path: Path) -> None:
    gold_v2 = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
    ov = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"
    if not gold_v2.is_file() or not CHRONO.is_file() or not ov.is_file():
        return
    ov_doc = json.loads(ov.read_text(encoding="utf-8"))
    if not (ov_doc.get("overrides") or []):
        return
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_hardset_news_era_gold_v2_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    out = tmp_path / "v2_proxy.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(gold_v2),
            "--chronology-json",
            str(CHRONO),
            "--tag-mode",
            "text_blind",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    hit = doc["summary"]["hit_at_1_strict"]
    assert hit is not None and float(hit) < 1.0
    gov = doc.get("governance") or {}
    assert "SELF_MATCH_GOLD_NO_HUMAN_OVERRIDE" not in (gov.get("flags") or [])
    assert "SUSPICIOUS_PERFECT_HIT_NO_HUMAN_GOLD" not in (gov.get("flags") or [])


def test_hardset_v2_text_blind_triggers_governance_warning(tmp_path: Path) -> None:
    news = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
    if not news.is_file() or not CHRONO.is_file():
        return
    empty_ov = tmp_path / "empty_overrides.json"
    empty_ov.write_text(
        json.dumps({"schema": "logos_chronology_hardset_era_gold_overrides_v1", "overrides": []}),
        encoding="utf-8",
    )
    gold_v2 = tmp_path / "gold_v2_heuristic_only.json"
    cp_build = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_logos_hardset_news_era_gold_v2_v1.py"),
            "--output-json",
            str(gold_v2),
            "--overrides-json",
            str(empty_ov),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp_build.returncode == 0, cp_build.stderr
    out = tmp_path / "v2_warn.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(gold_v2),
            "--chronology-json",
            str(CHRONO),
            "--tag-mode",
            "text_blind",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "warning"
    gov = doc.get("governance") or {}
    assert "SELF_MATCH_GOLD_NO_HUMAN_OVERRIDE" in (gov.get("flags") or [])


def test_era_blind_eval_rag_assisted_smoke(tmp_path: Path) -> None:
    gold_v2 = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
    if not gold_v2.is_file() or not CHRONO.is_file():
        return
    out = tmp_path / "rag_assisted.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(gold_v2),
            "--chronology-json",
            str(CHRONO),
            "--tag-mode",
            "rag_assisted",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["tag_mode"] == "rag_assisted"
    assert doc["inputs"].get("graphrag_topics_json")


def test_tier_v2_ssot_merge_runs() -> None:
    gold_v2 = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
    if not gold_v2.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_chronology_tier_v2_ssot_merge_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    primary = ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
    assert primary.is_file()
    doc = json.loads(primary.read_text(encoding="utf-8"))
    assert (doc.get("inputs") or {}).get("boost_policy") == "tier_v2_locked_eval"
    baseline = ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json"
    assert baseline.is_file()


def test_historical_tier_v2_ab_runs() -> None:
    if not GOLD.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_chronology_historical_tier_v2_ab_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    out = ROOT / "reports/logos_chronology_historical_tier_v2_ab_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ms_citation_contract"]["tier_v2_must_not_replace_ms_headline"] is True
    assert doc["ms_citation_contract"]["baseline_contaminated_by_tier_v2"] is False


def test_dynamic_map_still_runs_after_core_extract() -> None:
    build = ROOT / "scripts/build_logos_chronology_dynamic_map_v1.py"
    macro = ROOT / "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json"
    if not build.is_file() or not CHRONO.is_file() or not macro.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(build), "--chronology-json", str(CHRONO), "--macro-json", str(macro)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
