"""Regression: MKM deep explore v1 (P0 3-lane skeleton)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/mkm_deep_explore_v1.py"


def test_slugify_and_dedupe() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mkm_deep_explore_v1 import dedupe_rows, slugify_query

    assert slugify_query("LTM Memory OS trends!") == "ltm_memory_os_trends"
    rows = [
        {"arxiv_id": "2506.11763", "lane": "concept"},
        {"arxiv_id": "2506.11763", "lane": "implementation"},
        {"repo_path": "docs/research/foo.md", "lane": "repo"},
        {"repo_path": "docs/research/foo.md", "lane": "repo"},
    ]
    out = dedupe_rows(rows)
    assert len(out) == 2


def test_lane_repo_finds_hybrid_docs() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mkm_deep_explore_v1 import lane_repo

    hits = lane_repo("hybrid memory deep research", max_results=5)
    assert hits
    assert all(h["lane"] == "repo" for h in hits)
    assert any("research" in h["repo_path"] for h in hits)


def test_lane_repo_scans_scripts_directory() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mkm_deep_explore_v1 import lane_repo

    hits = lane_repo("deep research citation lock", max_results=10)
    assert any(h["repo_path"].startswith("scripts/") for h in hits)


def test_offline_dry_run_exit_zero() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--query",
            "hybrid memory OS",
            "--offline",
            "--dry-run",
            "--min-rows",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(r.stdout.strip())
    assert doc["ok"] is True
    assert doc["lane_stats"]["repo"] >= 1


def test_online_mock_arxiv_and_repo(monkeypatch) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import mkm_deep_explore_v1 as mod

    def fake_arxiv(query: str, lane: str, *, max_results: int, timeout: float):
        return [
            mod._make_arxiv_row(
                lane=lane,
                query=query,
                paper={
                    "arxiv_id": "2506.11763" if lane == "concept" else "2310.08560",
                    "title": f"paper-{lane}",
                    "summary": "summary",
                    "url": "https://arxiv.org/abs/x",
                },
                idx=1,
            )
        ], None

    monkeypatch.setattr(mod, "lane_arxiv", fake_arxiv)
    manifest, rows, ok = mod.explore(
        "memory OS",
        max_per_lane=2,
        timeout=1.0,
        offline=False,
        raw_dir=ROOT / "docs/research/raw",
        write_md=True,
    )
    assert ok is True
    assert manifest["deduped_count"] >= 3
    assert any(r.get("arxiv_id") == "2506.11763" for r in rows)


def test_write_md_stub_contains_arxiv_table(tmp_path: Path) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mkm_deep_explore_v1 import write_md_stub

    rows = [
        {
            "arxiv_id": "2506.11763",
            "lane": "concept",
            "title": "DeepResearch Bench",
        }
    ]
    out = tmp_path / "stub.md"
    write_md_stub(out, "test query", rows)
    text = out.read_text(encoding="utf-8")
    assert "2506.11763" in text
    assert "check_research_lit_review_citation_lock_v1.py" in text


def test_lane_repo_skips_historical_pin_env_without_file_not_found() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mkm_deep_explore_v1 import lane_repo

    hits = lane_repo("provenance evidence binding auditable AI LIT_REVIEW", max_results=8)
    assert isinstance(hits, list)
    assert not any("moonshot_pccc_gate0/gate0_5/pins/envs" in h.get("repo_path", "") for h in hits)
