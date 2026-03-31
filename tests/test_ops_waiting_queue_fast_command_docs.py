from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "run_waiting_queue_verify_fast.ps1"
OPS_COMMANDS = ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "OPS_COMMANDS.md"


def test_waiting_queue_fast_wrapper_exists_and_has_default_skips():
    assert WRAPPER.is_file(), f"missing wrapper: {WRAPPER}"
    text = WRAPPER.read_text(encoding="utf-8", errors="ignore")
    assert "-SkipBundle" in text
    assert "-SkipNightWatchmanHarness" in text
    assert "$NoSkipBundle" in text
    assert "$NoSkipNightWatchmanHarness" in text


def test_ops_commands_mentions_fast_waiting_queue_command():
    assert OPS_COMMANDS.is_file(), f"missing ops commands: {OPS_COMMANDS}"
    text = OPS_COMMANDS.read_text(encoding="utf-8", errors="ignore")
    assert "Fast Waiting-Queue Verification (Observability)" in text
    assert "run_waiting_queue_verify_fast.ps1" in text
