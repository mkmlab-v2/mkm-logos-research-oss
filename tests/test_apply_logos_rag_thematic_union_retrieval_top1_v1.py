"""Tests for apply_logos_rag_thematic_union_retrieval_top1_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_logos_rag_thematic_union_retrieval_top1_v1.py"


def test_union_script_dry_run_exit_zero(tmp_path: Path) -> None:
    gold = {
        "schema": "logos_semantic_query_gold_human_v1",
        "items": [
            {
                "id": "q05",
                "query_ko": "장기적 압박 속 소망의 징표",
                "gold_verse_ids_human": ["Prov.26.6", "Prov.26.3", "Job.38.28"],
            }
        ],
    }
    eval_doc = {
        "profiles": [
            {
                "mode": "ko_improved_vs_thematic_gold",
                "rows": [
                    {
                        "id": "q05",
                        "top_match_verse_id": "Eccl.7.3",
                        "weak_gold_hit_at_1": False,
                        "weak_gold_hit_at_3": True,
                    }
                ],
            }
        ]
    }
    gold_path = tmp_path / "gold.json"
    eval_path = tmp_path / "eval.json"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    eval_path.write_text(json.dumps(eval_doc), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gold-json",
            str(gold_path),
            "--eval-json",
            str(eval_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    after = json.loads(gold_path.read_text(encoding="utf-8"))
    assert after["items"][0]["gold_verse_ids_human"][0] == "Eccl.7.3"
