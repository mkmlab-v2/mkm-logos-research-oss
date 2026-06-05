"""Dan.2 empire_transition human sign-off promotion smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/promote_logos_graphrag_empire_transition_dan2_signoff_v1.py"
TRIAL_BUILDER = ROOT / "scripts/build_logos_graphrag_empire_transition_dan2_trial_v1.py"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"


def test_promote_dan2_signoff_dry_run(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(TRIAL_BUILDER)], cwd=str(ROOT), check=True)
    target = tmp_path / "dan2_promoted.json"
    signoff = tmp_path / "signoff.json"
    topics = tmp_path / "topics.json"
    gold = tmp_path / "gold.json"
    gold.write_text(GOLD.read_text(encoding="utf-8"), encoding="utf-8")
    topics.write_text(TOPICS.read_text(encoding="utf-8"), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--target-json",
            str(target),
            "--out-signoff",
            str(signoff),
            "--topics-fixture",
            str(topics),
            "--gold-fixture",
            str(gold),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    body = json.loads(cp.stdout.strip().splitlines()[-1])
    assert body.get("ok") is True
    assert body.get("dry_run") is True


def test_promote_dan2_requires_acknowledge(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(TRIAL_BUILDER)], cwd=str(ROOT), check=True)
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target-json",
            str(tmp_path / "out.json"),
            "--out-signoff",
            str(tmp_path / "signoff.json"),
            "--topics-fixture",
            str(tmp_path / "topics.json"),
            "--gold-fixture",
            str(tmp_path / "gold.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 2
