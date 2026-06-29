from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_corpus_4d_topology_v1.py"


def test_build_logos_corpus_4d_topology_v1_runs() -> None:
    out = ROOT / "reports/tmp_logos_topology_summary_test.json"
    verses = ROOT / "reports/tmp_logos_topology_verses_test.jsonl"
    hub = ROOT / "reports/tmp_logos_topology_hub_test.json"
    for p in (out, verses, hub):
        if p.is_file():
            p.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out),
            "--verses-jsonl",
            str(verses),
            "--hub-public-json",
            str(hub),
            "--corpus-limit",
            "128",
            "--top-hubs",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_corpus_4d_topology_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    assert doc["research_only"] is True
    assert doc["n_verses"] == 128
    assert len(doc["global_centrality_hubs"]) == 10
    assert len(doc["era_centroid_trajectories"]) >= 1
    lines = [ln for ln in verses.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 128
    hub_doc = json.loads(hub.read_text(encoding="utf-8"))
    assert hub_doc["schema"] == "logos_corpus_4d_topology_hub_v1"
