from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_btrack_logos_music_overlay_poc_v1.py"
PAIRS = ROOT / "tests" / "fixtures" / "lens_music_prompt_poc_pairs_sample_v1.jsonl"
BATCH = ROOT / "tests" / "fixtures" / "logos_4lens_batch_minimal_v1.json"


def _write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_overlay_poc_passes_with_minimal_logos_and_sample_pairs(tmp_path: Path) -> None:
    logos = tmp_path / "logos.json"
    out = tmp_path / "poc_out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lens_logos.py"),
            "--batch-json",
            str(BATCH),
            "--output",
            str(logos),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr

    cp2 = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pairs-jsonl",
            str(PAIRS),
            "--logos-lens",
            str(logos),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stdout + cp2.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_logos_music_overlay_poc_v1"
    assert doc["metrics"]["citation_violation_rate"] == 0.0


def test_overlay_poc_fails_when_overlay_cites_unknown_verse(tmp_path: Path) -> None:
    logos = tmp_path / "logos.json"
    pairs = tmp_path / "pairs.jsonl"
    out = tmp_path / "poc_out.json"

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lens_logos.py"),
            "--batch-json",
            str(BATCH),
            "--output",
            str(logos),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0

    pairs.write_text(
        '{"id":"bad1","baseline_response_text":"ok","overlay_response_text":"See ROM.8.28 for context."}\n',
        encoding="utf-8",
    )

    cp2 = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pairs-jsonl",
            str(pairs),
            "--logos-lens",
            str(logos),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["metrics"]["citation_violation_count"] >= 1
