from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_integrate_chain_dry_run_exit_zero():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "run_logos_theme_integrate_chain_v1.py"),
        "--dry-run",
    ]
    cp = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    assert "dry_run" in cp.stdout


def test_integrate_chain_stop_file_skips(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    db = tmp_path / "db"
    db.mkdir()
    stop = db / "LOGOS_THEME_RUN.stop"
    stop.write_text("stop\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(root / "scripts" / "run_logos_theme_integrate_chain_v1.py"),
        "--db-dir",
        str(db),
        "--skip-deploy",
    ]
    cp = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    assert "STOP file" in cp.stdout


def test_backlog_expand_template_one_theme(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    db = tmp_path / "db"
    db.mkdir()
    backlog = db / "theme_backlog_v1.jsonl"
    entry = {
        "theme_num": 99,
        "slug": "test_stub",
        "status": "pending",
        "theme": "Test Stub (Track B)",
        "anchor_ref": "요한복음 3:16",
        "anchor_text": "하나님이 세상을 이처럼 사랑하사",
        "anchor_node_id": "ANCHOR_JHN_3_16",
        "ops_analogy_note": "테스트 스텁 — 운영 게이트와 무관.",
        "semantic_nodes": [
            {
                "ref": "요한복음 3:17",
                "text": "구원을 얻게 하려 하심이라",
                "edge_type": "is_purpose_of",
                "research_metaphor_logic_connection": "test link",
                "research_metaphor_domain": "research_metaphor_test_stub",
            }
        ],
    }
    backlog.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(root / "scripts" / "run_logos_theme_backlog_expand_v1.py"),
        "--backlog",
        str(backlog),
        "--db-dir",
        str(db),
        "--max-per-run",
        "1",
    ]
    cp = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = db / "theme_99_test_stub.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["meta"]["gating_status"] == "NON_GATING"
