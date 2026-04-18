from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_btc_promotion_search_smoke() -> None:
    ws = Path(__file__).resolve().parents[1]
    out = ws / "docs" / "final" / "artifacts" / "_tmp_prophecy_btc_promotion_search_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_btc_promotion_search_v1.py"),
            "--n-folds-grid",
            "4,5",
            "--objective-grid",
            "margin_vs_bull,accuracy",
            "--top-k",
            "3",
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_btc_promotion_search_v1"
    assert isinstance(doc.get("top_candidates"), list)

