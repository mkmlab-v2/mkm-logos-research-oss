# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.8}
# Balance: 90
# Purpose: Regression test for note semantic memory SQLite index/query scripts.
# Keywords: pytest, sqlite, memory, context, retrieval

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_context_note_memory_index_v1.py"
QUERY = ROOT / "scripts" / "query_context_note_memory_index_v1.py"


def test_build_and_query_note_memory_index_hash_stub(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "auth.md").write_text(
        "JWT decision\n\nWe selected JWT for stateless auth and better horizontal scaling.",
        encoding="utf-8",
    )
    (notes_dir / "tradeoff.md").write_text(
        "Auth tradeoffs\n\nJWT revocation is hard, so we track short TTL and rotation.",
        encoding="utf-8",
    )

    sqlite_out = tmp_path / "note_memory.sqlite"
    relations_out = tmp_path / "relations.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--glob",
            f"{notes_dir.as_posix()}/**/*.md",
            "--max-files",
            "20",
            "--vector-dim",
            "64",
            "--sqlite-out",
            str(sqlite_out),
            "--relations-json",
            str(relations_out),
            "--exclude-glob",
            "**/do-not-match/**",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    assert sqlite_out.is_file()
    assert relations_out.is_file()

    con = sqlite3.connect(str(sqlite_out))
    try:
        cnt = con.execute("SELECT COUNT(*) FROM note_chunks").fetchone()[0]
        assert cnt >= 2
    finally:
        con.close()

    qp = subprocess.run(
        [
            sys.executable,
            str(QUERY),
            "--sqlite",
            str(sqlite_out),
            "--query",
            "JWT authentication decision",
            "--top-k",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert qp.returncode == 0, qp.stderr
    doc = json.loads(qp.stdout)
    assert doc.get("schema") == "context_note_query_result_v1"
    assert len(doc.get("top_k", [])) >= 1

