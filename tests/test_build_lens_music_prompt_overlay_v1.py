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
    hormone_state_path = tmp_path / "hormone_state.json"
    hist = tmp_path / "hist.jsonl"
    smoke = tmp_path / "smoke.json"
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
    smoke.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_smoke_eval_v1",
                "state": "WATCH",
                "style_match_rate": 0.2,
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
            "--smoke-eval-json",
            str(smoke),
            "--out",
            str(out),
            "--state-json",
            str(state_path),
            "--hormone-state-json",
            str(hormone_state_path),
            "--history-log-jsonl",
            str(hist),
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
    assert doc["global_state"]["style"]["temperature_hint"] <= 0.45
    hormone = doc["global_state"]["hormone_like_state"]
    assert hormone["schema"] == "lens_music_hormone_state_v1"
    assert hormone["state"] in {"STABLE", "ELEVATED", "HIGH_STRESS"}
    assert 0.0 <= float(hormone["stress_index_0_1"]) <= 1.0
    assert 0.0 <= float(hormone["recovery_buffer_0_1"]) <= 1.0
    assert "metaphor_only" in hormone["non_biological_notice"]
    gtr = doc["global_state"]["gematria_seed_trace"]
    assert gtr["schema"] == "lens_music_gematria_seed_trace_v1"
    assert gtr["present"] is False
    assert gtr["applied_ema_alpha_multiplier"] == 1.0
    assert float(gtr["effective_hormone_ema_alpha"]) == 0.4
    assert hormone["gematria_seed_trace"]["applied_ema_alpha_multiplier"] == 1.0
    assert doc["global_state"]["m31_audit_trail"]["schema"] == "lens_music_m31_audit_trail_v1"
    assert doc["global_state"]["m31_audit_trail"]["rag_metabolism_drift"]["source"] == "synthetic_baseline"
    assert doc["control_plane_contract"]["control_plane_user_plane_separation"] is True
    assert doc["auto_brake_m22"]["active"] is True
    assert doc["auto_brake_m22"]["trigger_smoke_eval_watch"] is True
    assert "Governance=WATCH" in doc["system_instructions"]
    lines = [x for x in hist.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema"] == "lens_music_prompt_overlay_history_row_v1"
    assert row["auto_brake_active"] is True
    assert row["hormone_state"] in {"STABLE", "ELEVATED", "HIGH_STRESS"}
    assert row["gematria_present"] is False
    assert row["gematria_applied_ema_alpha_multiplier"] == 1.0
    assert row["gematria_effective_hormone_ema_alpha"] == 0.4
    assert row["rag_metabolism_source"] == "synthetic_baseline"
    assert isinstance(row["rag_metabolism_bounded_drift_0_1"], float)
    assert 0.0 <= float(row["rag_metabolism_bounded_drift_0_1"]) <= 0.25


def test_build_overlay_gematria_trace_m32_multiplier_on_hormone_ema():
    from scripts.build_lens_music_prompt_overlay_v1 import build_overlay

    gov = {"schema": "lens_music_audition_governance_status_v1", "state": "GO"}
    chain = {
        "schema": "lens_music_gate_chain_v1",
        "gematria_seed_trace": {
            "schema": "lens_music_gematria_seed_trace_v1",
            "seed_source": "lens_music_gematria_v1",
            "present": True,
            "verse_or_token_ref": "taeeum",
            "numeric_value": 207,
        },
        "melody_stage_m9": {
            "input_snapshot": {"tempo_target_bpm": 90.0, "valence": 0.0, "arousal": 0.0}
        },
    }
    doc, _, _ = build_overlay(
        gov,
        chain,
        smoke_eval={"schema": "lens_music_prompt_smoke_eval_v1", "state": "GO"},
        prev_hormone=None,
        ema_alpha=0.4,
    )
    gt = doc["global_state"]["gematria_seed_trace"]
    assert gt["numeric_value"] == 207
    assert gt["applied_ema_alpha_multiplier"] == 1.024
    assert abs(float(gt["effective_hormone_ema_alpha"]) - 0.4096) < 1e-9
    h = doc["global_state"]["hormone_like_state"]
    assert h["gematria_seed_trace"]["applied_ema_alpha_multiplier"] == 1.024
    trail = doc["global_state"]["m31_audit_trail"]
    assert trail["schema"] == "lens_music_m31_audit_trail_v1"
    assert trail["rag_metabolism_drift"]["source"] == "synthetic_baseline"


def test_build_overlay_rag_digest_override_chain_doc() -> None:
    from scripts.build_lens_music_prompt_overlay_v1 import build_overlay

    gov = {"schema": "lens_music_audition_governance_status_v1", "state": "GO"}
    chain = {
        "schema": "lens_music_gate_chain_v1",
        "rag_metabolism_digest_v1": {
            "bounded_drift_0_1": 0.12,
            "source": "chain_doc_rag_digest",
            "digest_fingerprint": "unit_test_fp",
        },
        "melody_stage_m9": {
            "input_snapshot": {"tempo_target_bpm": 90.0, "valence": 0.0, "arousal": 0.0}
        },
    }
    doc, _, _ = build_overlay(
        gov,
        chain,
        smoke_eval={"schema": "lens_music_prompt_smoke_eval_v1", "state": "GO"},
        prev_hormone=None,
        ema_alpha=0.4,
    )
    drift = doc["global_state"]["m31_audit_trail"]["rag_metabolism_drift"]
    assert drift["source"] == "chain_doc_rag_digest"
    assert drift["bounded_drift_0_1"] == 0.12
    assert drift["digest_fingerprint"] == "unit_test_fp"


def test_build_gematria_seed_trace_from_lens_doc():
    from scripts.run_lens_music_gematria_gate_chain_v1 import build_gematria_seed_trace_from_lens_doc

    lens_doc = {
        "schema": "lens_music_gematria_v1",
        "resolution": "builtin_sasang_table_v1",
        "ts_utc": "2026-05-12T00:00:00Z",
        "hypothesis_tier": "B",
        "provenance": {"source": "builtin_table", "experiment_id": "x"},
        "sasang_music_mapping_v1": {
            "inputs": {"sasang_primary": "taeeum", "gematria_total_optional": 33},
        },
    }
    t = build_gematria_seed_trace_from_lens_doc(lens_doc)
    assert t["present"] is True
    assert t["numeric_value"] == 33
    assert t["verse_or_token_ref"] == "taeeum"
