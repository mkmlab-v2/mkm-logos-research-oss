# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_approve_weather_fusion_profile_flow(tmp_path: Path):
    profile = tmp_path / "profile.json"
    lock = tmp_path / "lock.json"
    log = tmp_path / "approval_log.jsonl"

    train_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "train_myeongni_weather_fusion_profile_v1.py"),
        "--output-json",
        str(profile),
    ]
    cp1 = subprocess.run(train_cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp1.returncode == 0, cp1.stderr or cp1.stdout

    approve_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "approve_myeongni_weather_fusion_profile_v1.py"),
        "--profile-json",
        str(profile),
        "--lock-out",
        str(lock),
        "--approval-log",
        str(log),
        "--reviewer",
        "test",
        "--approve",
    ]
    cp2 = subprocess.run(approve_cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp2.returncode == 0, cp2.stderr or cp2.stdout

    pdoc = json.loads(profile.read_text(encoding="utf-8"))
    assert pdoc["policy"]["allow_apply"] is True
    assert pdoc["policy"]["human_signoff_ack"] is True
    ldoc = json.loads(lock.read_text(encoding="utf-8"))
    assert ldoc["decision"] == "approved"
    assert log.exists()

