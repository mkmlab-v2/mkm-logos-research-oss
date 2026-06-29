"""Regression: P1-D raw drop delta + incremental re-merge + gate chain."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_MERGED = ROOT / "tests/fixtures/research_merged_remerge_base_v1.md"
NEW_RAW = ROOT / "tests/fixtures/research_raw_drop_new_v1.md"
RAW_DELTA = ROOT / "scripts/build_mkm_raw_drop_delta_v1.py"
INCREMENTAL = ROOT / "scripts/build_mkm_merged_lit_review_incremental_v1.py"
REMERGE_CHAIN = ROOT / "scripts/run_mkm_merged_lit_review_remerge_chain_v1.py"
SHALLOW_TRIGGER = ROOT / "scripts/build_mkm_raw_drop_shallow_trigger_v1.py"


def test_raw_drop_delta_regex_no_ollama(tmp_path: Path) -> None:
    out = tmp_path / "delta.json"
    r = subprocess.run(
        [
            sys.executable,
            str(RAW_DELTA),
            "--input",
            str(NEW_RAW),
            "--baseline-md",
            str(BASE_MERGED),
            "--no-ollama",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_raw_drop_delta_v1"
    assert "2508.12752" in doc["arxiv_ids"]
    assert "2508.12752" in doc["new_arxiv_ids"]
    assert doc["extract_mode"] == "regex"
    assert any(row["filter"] == "NARROW" for row in doc["overclaim_candidates"])


def test_incremental_merge_adds_new_arxiv(tmp_path: Path) -> None:
    merged = tmp_path / "merged.md"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    shutil.copy(BASE_MERGED, merged)
    manifest = tmp_path / "fixture_remerge_remerge_manifest_latest.json"

    bootstrap = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr + bootstrap.stdout

    shutil.copy(NEW_RAW, raw_dir / "research_raw_drop_new_v1.md")
    r = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(r.stdout.strip())
    assert doc["changed"] is True
    assert "2508.12752" in doc["new_arxiv_ids"]
    text = merged.read_text(encoding="utf-8")
    assert "2508.12752" in text
    assert "Part VI.G" in text


def test_remerge_noop_when_manifest_current(tmp_path: Path) -> None:
    merged = tmp_path / "merged.md"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    shutil.copy(BASE_MERGED, merged)
    raw_path = raw_dir / "research_raw_drop_new_v1.md"
    shutil.copy(NEW_RAW, raw_path)

    manifest_dir = tmp_path / "artifacts"
    manifest_dir.mkdir()
    manifest = manifest_dir / "fixture_remerge_remerge_manifest_latest.json"

    first = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stderr + first.stdout

    second = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, second.stderr + second.stdout
    doc = json.loads(second.stdout.strip())
    assert doc["changed"] is False


def test_raw_drop_shallow_trigger_fixture(tmp_path: Path) -> None:
    trigger_out = tmp_path / "trigger.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SHALLOW_TRIGGER),
            "--merged",
            str(BASE_MERGED),
            "--topic-slug",
            "fixture_remerge",
            "--raw-path",
            str(NEW_RAW),
            "--query",
            "memory OS survey",
            "--no-ollama",
            "--skip-handoff",
            "--out-json",
            str(trigger_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(trigger_out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_raw_drop_shallow_trigger_v1"
    assert doc["lane_priority"][0] == "concept"
    assert doc["domain_tag"] in {"oracle", "infra", "devops", "design"}
    assert "2508.12752" in doc["new_arxiv_ids"]


def test_remerge_bootstrap_manifest_no_patch(tmp_path: Path) -> None:
    merged = tmp_path / "merged.md"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    shutil.copy(BASE_MERGED, merged)
    shutil.copy(NEW_RAW, raw_dir / "research_raw_drop_new_v1.md")
    (raw_dir / "hybrid_edge_cloud_llm_memory_explore_2026-06-20.md").write_text(
        "arxiv:9999.99999 explore artifact\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "fixture_remerge_remerge_manifest_latest.json"
    before = merged.read_text(encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(r.stdout.strip())
    assert doc["bootstrapped"] is True
    assert doc["changed"] is False
    assert merged.read_text(encoding="utf-8") == before
    manifest_doc = json.loads(manifest.read_text(encoding="utf-8"))
    paths = {row["path"] for row in manifest_doc["raw_files"]}
    assert any("research_raw_drop_new_v1.md" in p for p in paths)
    assert not any("_explore_" in p for p in paths)


def test_remerge_chain_offline_fixture(tmp_path: Path) -> None:
    scratch = ROOT / "reports" / f"pytest_remerge_{tmp_path.name}"
    scratch.mkdir(parents=True, exist_ok=True)
    merged = scratch / "merged.md"
    raw_dir = scratch / "raw"
    manifest = scratch / "fixture_remerge_remerge_manifest_latest.json"
    raw_dir.mkdir()
    shutil.copy(BASE_MERGED, merged)

    bootstrap = subprocess.run(
        [
            sys.executable,
            str(INCREMENTAL),
            "--merged",
            str(merged),
            "--raw-dir",
            str(raw_dir),
            "--topic-slug",
            "fixture_remerge",
            "--manifest",
            str(manifest),
            "--offline",
            "--no-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr + bootstrap.stdout
    shutil.copy(NEW_RAW, raw_dir / "research_raw_drop_new_v1.md")

    out_json = scratch / "remerge_chain.json"
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(REMERGE_CHAIN),
                "--merged",
                str(merged),
                "--raw-dir",
                str(raw_dir),
                "--topic-slug",
                "fixture_remerge",
                "--manifest",
                str(manifest),
                "--offline",
                "--no-ollama",
                "--skip-handoff",
                "--out-json",
                str(out_json),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        chain = json.loads(out_json.read_text(encoding="utf-8"))
        assert chain["ok"] is True
        assert chain["incremental_patch"]["changed"] is True
        assert chain["shallow_trigger"]["ok"] is True
        assert chain["gate_chain"]["ok"] is True
        assert chain["gate_chain"]["citation_lock"]["ok"] is True
        assert chain["gate_chain"]["fact_support"]["ok"] is True
        assert chain["dr_bench_mini"]["ok"] is True
        assert chain["bench_skipped"] is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
