#!/usr/bin/env python3
"""RQ-019 internal M2M pipe upgrade v0 — Trust Packet v0.2 + roundtrip + pytest.

Writes docs/final/artifacts/mkm_rq019_m2m_pipe_upgrade_v0_latest.json
Track B · research_only · send_gate HOLD. Extends existing stub; no multimodal.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mkm_rq019_m2m_pipe_upgrade_v0_latest.json"
TEST = "tests/test_rq019_m2m_pipe_upgrade_v0.py"
THIN_SMOKE = ROOT / "scripts/run_rq019_trust_packet_thin_smoke_v0.py"
ROUNDTRIP = ROOT / "scripts/run_rq019_m2m_two_agent_roundtrip_v0.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    pytest_proc = _run([sys.executable, "-m", "pytest", "-q", TEST])
    thin_proc = _run([sys.executable, str(THIN_SMOKE)])
    rt_pass = _run(
        [sys.executable, str(ROUNDTRIP), "--expect-pass", "--out", str(
            ROOT / "docs/final/artifacts/mkm_rq019_m2m_two_agent_roundtrip_v0_latest.json"
        )]
    )
    rt_oov = _run(
        [
            sys.executable,
            str(ROUNDTRIP),
            "--inject-oov",
            "--expect-hold",
            "--out",
            str(
                ROOT
                / "docs/final/artifacts/mkm_rq019_m2m_two_agent_roundtrip_oov_hold_v0_latest.json"
            ),
        ]
    )

    pytest_ok = pytest_proc.returncode == 0
    thin_ok = thin_proc.returncode == 0
    rt_pass_ok = rt_pass.returncode == 0
    rt_oov_ok = rt_oov.returncode == 0
    all_ok = pytest_ok and thin_ok and rt_pass_ok and rt_oov_ok

    artifact = {
        "schema": "mkm_rq019_m2m_pipe_upgrade_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tag": "[HYPO]",
        "program": "RQ-019 internal M2M pipe upgrade · Trust Packet v0.2 thin",
        "shipped": [
            "trust_packet_v0_2_envelope",
            "two_agent_encode_expand_roundtrip",
            "oov_hold_path",
            "regression_pytest",
        ],
        "not_shipped": [
            "multimodal",
            "m2m_100",
            "lingua_franca",
            "track_c",
            "41k_ontology",
            "domain_a_b_merged_product",
            "production_sla",
        ],
        "trust_packet_v0_2": {
            "module": "scripts/mkm_rq019_trust_packet_v02.py",
            "packet_format_version": "trust_packet.0.2",
            "inner_unchanged": "trust_packet.0.1",
            "fields": [
                "packet_format_version",
                "codebook_id",
                "codebook_version",
                "allowlist_ref",
                "hold_decision",
                "oov_tokens",
                "compression_packet",
            ],
            "schema_path": "docs/final/schemas/mkm_trust_packet_envelope_v0_2.schema.json",
        },
        "roundtrip": {
            "script": "scripts/run_rq019_m2m_two_agent_roundtrip_v0.py",
            "pass_exit_code": rt_pass.returncode,
            "pass_ok": rt_pass_ok,
            "oov_hold_exit_code": rt_oov.returncode,
            "oov_hold_ok": rt_oov_ok,
            "pass_artifact": "docs/final/artifacts/mkm_rq019_m2m_two_agent_roundtrip_v0_latest.json",
            "oov_artifact": "docs/final/artifacts/mkm_rq019_m2m_two_agent_roundtrip_oov_hold_v0_latest.json",
        },
        "thin_smoke_reuse": {
            "script": "scripts/run_rq019_trust_packet_thin_smoke_v0.py",
            "exit_code": thin_proc.returncode,
            "ok": thin_ok,
        },
        "pytest": {
            "test_file": TEST,
            "exit_code": pytest_proc.returncode,
            "ok": pytest_ok,
            "stdout_tail": (pytest_proc.stdout or "")[-1500:],
            "stderr_tail": (pytest_proc.stderr or "")[-800:],
        },
        "pointers": {
            "wire_profile": "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
            "encoding_status": "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
            "hold_ledger": "docs/final/artifacts/mkm_hold_strong_qe_mission_ledger_v0_latest.md",
            "onepager": "docs/final/artifacts/mkm_rq019_m2m_pipe_upgrade_v0_onepager.md",
            "stub": "scripts/compression_token_api_v2_stub.py",
            "domain_a_allowlist_gate": "scripts/run_policy_allowlist_hold_gate_v0.py",
        },
        "walls": [
            "not_multimodal",
            "not_m2m_100",
            "not_track_c",
            "not_41k_ontology",
            "not_lingua_franca",
            "not_domain_a_b_merged_product",
            "not_production_sla",
            "send_gate_HOLD",
            "domain_a_allowlist_HOLD_intact",
        ],
        "all_ok": all_ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": all_ok,
                "pytest_exit_code": pytest_proc.returncode,
                "thin_smoke_exit_code": thin_proc.returncode,
                "roundtrip_pass_exit_code": rt_pass.returncode,
                "roundtrip_oov_exit_code": rt_oov.returncode,
                "artifact": str(OUT.as_posix()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
