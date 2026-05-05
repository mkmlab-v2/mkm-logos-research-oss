from pathlib import Path

from scripts.validate_mkm_11axis_report_v1 import main


def _write_report(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "report.md"
    p.write_text(body, encoding="utf-8")
    return p


def _build_min_report(final_action: str = "HOLD", fail_axis_9: bool = False) -> str:
    parts = ["# Report", ""]
    for axis in range(1, 12):
        parts.append(f"## Axis {axis} - X")
        if fail_axis_9 and axis == 9:
            parts.append("- verdict: [FACT] FAIL due to high friction")
        else:
            parts.append("- verdict: [FACT] pass")
        parts.append("")
    parts.append("## Final Decision")
    parts.append(f"- action: {final_action}")
    parts.append("- reason: test")
    return "\n".join(parts)


def test_validator_accepts_valid_report(monkeypatch, tmp_path: Path) -> None:
    report = _write_report(tmp_path, _build_min_report(final_action="HOLD"))
    monkeypatch.setattr("sys.argv", ["validate_mkm_11axis_report_v1.py", str(report)])
    assert main() == 0


def test_validator_rejects_non_hold_on_axis9_fact_fail(monkeypatch, tmp_path: Path) -> None:
    report = _write_report(tmp_path, _build_min_report(final_action="GO", fail_axis_9=True))
    monkeypatch.setattr("sys.argv", ["validate_mkm_11axis_report_v1.py", str(report)])
    assert main() == 6
