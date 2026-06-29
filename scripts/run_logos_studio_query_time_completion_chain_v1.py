#!/usr/bin/env python3
"""Completion chain: query-time GraphRAG + Studio UX + smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_studio_query_time_completion_chain_v1_latest.json"


def main() -> int:
    steps = [
        ("graphrag_encode_smoke", [PY, "scripts/encode_logos_studio_query_graphrag_v1.py", "--query", "소망 인내"]),
        ("conflict_retrieve_smoke", [PY, "scripts/retrieve_logos_studio_conflict_context_v1.py", "--query", "네피림", "--no-embedding"]),
        ("conflict_retrieval_gate", [PY, "scripts/check_logos_studio_conflict_retrieval_gate_v1.py"]),
        ("mobile_cache_chain", [PY, "scripts/run_logos_studio_mobile_and_cache_chain_v1.py"]),
        ("pytest_graphrag", [PY, "-m", "pytest", "tests/test_logos_studio_query_time_graphrag_v1.py", "-q"]),
        ("pytest_conflict", [PY, "-m", "pytest", "tests/test_logos_studio_conflict_retrieval_v1.py", "-q"]),
        ("pytest_synthesis", [PY, "-m", "pytest", "tests/test_logos_studio_dynamic_synthesis_v1.py", "-q"]),
        ("pytest_embedding", [PY, "-m", "pytest", "tests/test_logos_studio_embedding_router_v1.py", "-q"]),
    ]
    results: list[dict] = []
    for label, cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT)
        results.append({"step": label, "exit_code": proc.returncode})
        if proc.returncode != 0:
            OUT.write_text(
                json.dumps({"ok": False, "steps": results}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return 1
    OUT.write_text(
        json.dumps(
            {
                "ok": True,
                "schema": "logos_studio_query_time_completion_chain_v1",
                "steps": results,
                "reproduce": "py scripts/run_logos_studio_query_time_completion_chain_v1.py",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
