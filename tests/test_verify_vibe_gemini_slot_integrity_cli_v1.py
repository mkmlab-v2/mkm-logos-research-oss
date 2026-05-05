"""CLI smoke for scripts/verify_vibe_gemini_slot_integrity_v1.py (no repo artifacts required)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "verify_vibe_gemini_slot_integrity_v1.py"


def _run_verify(tmp: Path, *, runs_lines: list[str], md_files: dict[str, str], args: list[str]) -> subprocess.CompletedProcess[str]:
    runs_path = tmp / "runs.jsonl"
    runs_path.write_text("\n".join(runs_lines) + "\n", encoding="utf-8")
    raw_dir = tmp / "raw"
    raw_dir.mkdir(parents=True)
    for name, body in md_files.items():
        (raw_dir / name).write_text(body, encoding="utf-8")
    out_json = tmp / "out.json"
    out_md = tmp / "out.md"
    cmd = [
        sys.executable,
        str(VERIFY),
        "--runs-jsonl",
        str(runs_path),
        "--raw-dir",
        str(raw_dir),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


_GOOD_MD = """# prompt_01_run_01.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.5
"""


def test_integrity_ok_with_strict_flags(tmp_path: Path) -> None:
    proc = _run_verify(
        tmp_path,
        runs_lines=[json.dumps({"prompt_id": "prompt_01", "run_index": 1})],
        md_files={"prompt_01_run_01.md": _GOOD_MD},
        args=["--require-runtime-header", "--fail-on-extra-files"],
    )
    assert proc.returncode == 0
    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"


def test_integrity_fails_on_stub_marker(tmp_path: Path) -> None:
    bad = _GOOD_MD + "\nresearch_stub_evidence_v1\n"
    proc = _run_verify(
        tmp_path,
        runs_lines=[json.dumps({"prompt_id": "prompt_01", "run_index": 1})],
        md_files={"prompt_01_run_01.md": bad},
        args=[],
    )
    assert proc.returncode == 2
    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert report["status"] == "fail"
    assert report["issues"]["stub_like_files"]


def test_integrity_fails_without_runtime_when_required(tmp_path: Path) -> None:
    plain = """# prompt_01_run_01.md

Final Action: HOLD
Confidence: 0.5
"""
    proc = _run_verify(
        tmp_path,
        runs_lines=[json.dumps({"prompt_id": "prompt_01", "run_index": 1})],
        md_files={"prompt_01_run_01.md": plain},
        args=["--require-runtime-header"],
    )
    assert proc.returncode == 2


def test_integrity_fails_on_extra_raw_files(tmp_path: Path) -> None:
    good02 = """# prompt_02_run_01.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.5
"""
    proc = _run_verify(
        tmp_path,
        runs_lines=[json.dumps({"prompt_id": "prompt_01", "run_index": 1})],
        md_files={
            "prompt_01_run_01.md": _GOOD_MD,
            "prompt_02_run_01.md": good02,
        },
        args=["--fail-on-extra-files"],
    )
    assert proc.returncode == 2
    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert report["issues"]["extra_files"]
