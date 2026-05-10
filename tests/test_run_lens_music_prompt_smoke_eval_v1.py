from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_lens_music_prompt_smoke_eval_sample_fixture(tmp_path):
    out = tmp_path / "smoke_eval.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_prompt_smoke_eval_v1.py"),
            "--samples-jsonl",
            str(ROOT / "tests/fixtures/lens_music_prompt_smoke_eval_sample_v1.jsonl"),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_smoke_eval_v1"
    assert doc["samples_count"] == 3
    assert doc["style_match_rate"] >= 0.66
