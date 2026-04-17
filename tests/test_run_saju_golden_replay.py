from pathlib import Path

from scripts.run_saju_golden_replay import run_replay


def test_run_saju_golden_replay_gate_passes():
    report = run_replay(Path("tests/fixtures/saju_golden_cases_v1.json"))
    assert report["summary"]["failed"] == 0
    assert report["summary"]["gate"] == "PASS"
    assert report["summary"]["total"] >= 4
