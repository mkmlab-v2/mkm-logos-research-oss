from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_prompt_overlay_from_governance_and_chain(tmp_path):
    gov = tmp_path / "gov.json"
    chain = tmp_path / "chain.json"
    out = tmp_path / "overlay.json"
    state_path = tmp_path / "state.json"
    gov.write_text(
        json.dumps(
            {
                "schema": "lens_music_audition_governance_status_v1",
                "state": "WATCH",
                "warn_ratio": 0.5,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    chain.write_text(
        json.dumps(
            {
                "schema": "lens_music_gate_chain_v1",
                "melody_stage_m9": {
                    "input_snapshot": {"tempo_target_bpm": 72.0, "valence": -0.2, "arousal": -0.4}
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lens_music_prompt_overlay_v1.py"),
            "--governance-json",
            str(gov),
            "--chain-json",
            str(chain),
            "--out",
            str(out),
            "--state-json",
            str(state_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_overlay_v1"
    assert doc["global_state"]["state"] == "WATCH"
    assert doc["global_state"]["smoothed_bpm"] > 0
    assert doc["global_state"]["target_bpm_from_sasang"] > 0
    assert doc["control_plane_contract"]["control_plane_user_plane_separation"] is True
    assert "Governance=WATCH" in doc["system_instructions"]
