# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.8}
# Balance: 90
# Purpose: Regression for hybrid note retrieval and MCP tool policy gate.
# Keywords: pytest, hybrid, mcp, policy, sqlite

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_context_note_memory_index_v1.py"
QUERY = ROOT / "scripts" / "query_context_note_memory_index_v1.py"
EVAL = ROOT / "scripts" / "eval_context_note_retrieval_v1.py"
MCP_GATE = ROOT / "scripts" / "enforce_mcp_tool_policy_v1.py"


def test_hybrid_and_eval_gate_and_mcp_policy(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "auth.md").write_text("JWT auth decision with short TTL rotation", encoding="utf-8")
    (notes_dir / "db.md").write_text("Postgres migration and schema strategy", encoding="utf-8")

    sqlite_out = tmp_path / "idx.sqlite"
    relations_out = tmp_path / "relations.json"
    build_cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--glob",
            f"{notes_dir.as_posix()}/**/*.md",
            "--sqlite-out",
            str(sqlite_out),
            "--relations-json",
            str(relations_out),
            "--vector-dim",
            "64",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_cp.returncode == 0, build_cp.stderr

    q_cp = subprocess.run(
        [
            sys.executable,
            str(QUERY),
            "--sqlite",
            str(sqlite_out),
            "--query",
            "JWT auth decision",
            "--retrieval-mode",
            "hybrid",
            "--top-k",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert q_cp.returncode == 0, q_cp.stderr
    q_doc = json.loads(q_cp.stdout)
    assert q_doc.get("retrieval_mode") == "hybrid"
    assert len(q_doc.get("top_k", [])) >= 1

    qrels = tmp_path / "qrels.json"
    qrels.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "query": "JWT auth decision",
                        "expected_paths": [str((notes_dir / "auth.md").resolve()).replace("\\", "/")],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    eval_out = tmp_path / "eval.json"
    e_cp = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--sqlite",
            str(sqlite_out),
            "--qrels-json",
            str(qrels),
            "--retrieval-mode",
            "hybrid",
            "--top-k",
            "2",
            "--min-precision-at-k",
            "0.0",
            "--min-recall-at-k",
            "0.0",
            "--out-json",
            str(eval_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert e_cp.returncode == 0, e_cp.stderr
    assert eval_out.is_file()

    policy = tmp_path / "mcp_policy.json"
    policy.write_text(
        json.dumps(
            {
                "allowlist": [{"server": "s1", "tool_name": "t1", "required_keys": ["query"]}],
                "required_arg_keys": [],
                "deny_arg_patterns": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    payload = tmp_path / "args.json"
    payload.write_text(json.dumps({"query": "hello"}, indent=2), encoding="utf-8")
    m_cp = subprocess.run(
        [
            sys.executable,
            str(MCP_GATE),
            "--policy-json",
            str(policy),
            "--server",
            "s1",
            "--tool-name",
            "t1",
            "--args-json",
            str(payload),
            "--out-json",
            str(tmp_path / "mcp_check.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert m_cp.returncode == 0, m_cp.stderr

