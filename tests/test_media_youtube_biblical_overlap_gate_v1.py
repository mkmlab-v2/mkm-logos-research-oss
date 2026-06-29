"""Biblical-polemic ingest chain + Tier A baseline overlap gate regression [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "tests/fixtures/media_youtube_biblical_polemic_ssot_v1.json"
TRANSCRIPT = ROOT / "tests/fixtures/youtube_transcript_polluted_full_v0.txt"
BASELINE = ROOT / "tests/fixtures/media_stt_transcription_polluted_bench_v1.json"
CHAIN = ROOT / "scripts/run_media_youtube_biblical_ingest_chain_v1.py"
EVAL = ROOT / "scripts/eval_media_youtube_overlap_gate_v1.py"
DIFF = ROOT / "scripts/build_media_youtube_ingest_diff_report_v0.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_media_youtube_overlap_gate_v1 import eval_tier_a_overlap_gate  # noqa: E402


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_biblical_ssot_tier_a_gate_and_tier_b_deferred() -> None:
    ssot = _read_json(SSOT)
    assert ssot["schema"] == "media_youtube_biblical_polemic_ssot_v1"
    assert ssot["send_gate"] == "HOLD"
    gate = ssot["overlap_gate_v1"]
    assert gate["overlap_window_sec"] == 120.0
    assert gate["scholarly_top3_proximity_min_pairs"] == 2
    assert gate["multilens_top3_proximity_min_pairs"] == 2
    assert gate["id_overlap_used_as_gate"] is False
    tier_b = ssot["logos_corpus_overlap_v1"]
    assert tier_b["promotion_gate"] is False
    assert tier_b["chain_status"] == "deferred_separate_module"
    artifacts = ssot["artifacts"]
    assert artifacts["overlap_report"].endswith("baseline_overlap_biblical_polemic_v1_latest.json")


def test_eval_tier_a_overlap_gate_passes_on_fixture_diff(tmp_path: Path) -> None:
    ssot = _read_json(SSOT)
    gate = ssot["overlap_gate_v1"]
    diff_out = tmp_path / "diff.json"
    overlap_out = tmp_path / "overlap.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(DIFF),
            "--input",
            str(TRANSCRIPT),
            "--out",
            str(diff_out),
            "--baseline",
            str(BASELINE),
            "--overlap-window-sec",
            str(gate["overlap_window_sec"]),
            "--theme",
            str(ssot["theme"]),
            "--wav-source",
            str(ssot["youtube_url"]),
            "--target-suite",
            str(ssot["target_suite"]),
            "--theme-keywords",
            ",".join(ssot["theme_keywords"]),
            "--negative-keywords",
            ",".join(ssot["negative_keywords"]),
            "--multilens-keywords",
            ",".join(ssot["multilens_keywords"]),
            "--merge-min-chars",
            str(ssot["merge_min_chars"]),
            "--merge-max-chars",
            str(ssot["merge_max_chars"]),
            "--task-id",
            str(ssot["default_task_id"]),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout

    diff_doc = _read_json(diff_out)
    report = eval_tier_a_overlap_gate(diff_doc, gate, ssot_path=str(SSOT.relative_to(ROOT)))
    assert report["tier_a_pass"] is True
    assert report["checks"]["scholarly_top3_proximity_min_pairs"] is True
    assert report["checks"]["multilens_top3_proximity_min_pairs"] is True
    assert report["measured"]["scholarly_top3_proximity"]["window_sec"] == 120.0
    assert report["measured"]["id_overlap_gate_status"] == "informational_only"

    proc2 = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--diff-report",
            str(diff_out),
            "--ssot",
            str(SSOT),
            "--out",
            str(overlap_out),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    overlap_doc = _read_json(overlap_out)
    assert overlap_doc["schema"] == "media_youtube_baseline_overlap_gate_v1"
    assert overlap_doc["tier_a_pass"] is True
    assert overlap_doc["tier_b_skipped"] is True


def test_biblical_ingest_chain_exit_0_and_tier_a_locked() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHAIN)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    tail = json.loads(proc.stdout.strip().splitlines()[-1])
    assert tail["ok"] is True
    assert tail["tier_a_pass"] is True
    assert tail["overlap_checks"]["scholarly_top3_proximity_min_pairs"] is True
    assert tail["validation"]["scholarly_lane_clean"] is True

    overlap_path = ROOT / str(tail["overlap_report"])
    overlap_doc = _read_json(overlap_path)
    assert overlap_doc["tier_a_pass"] is True
    assert overlap_doc["gate_spec"]["overlap_window_sec"] == 120.0

    handoff = ROOT / "reports/handoff_workers/HW-20260621-YT-BIBLICAL-LOGOS_CLIP.md"
    assert handoff.is_file()
    assert "send_gate: HOLD" in handoff.read_text(encoding="utf-8")
