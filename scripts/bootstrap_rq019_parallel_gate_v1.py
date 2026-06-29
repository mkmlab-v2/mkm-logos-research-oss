#!/usr/bin/env python3
"""Bootstrap missing RQ-019 gate artifacts and refresh dependent JSON (B-track only)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENVELOPE_EXAMPLE = ROOT / "docs/final/artifacts/fixtures/mkm_inter_agent_wire_envelope_v1.example.json"
KO_LEXICON = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_lexicon_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_envelope_fixture() -> dict:
    from scripts.mkm_inter_agent_wire_envelope_v1 import build_turn_envelope
    from scripts.validate_mkm_inter_agent_wire_envelope_v1 import validate_doc

    env = build_turn_envelope(
        encode_response={
            "wire_b64": "dGVzdA==",
            "wire_byte_len": 4,
            "codec_variant": "none",
            "atom_id_sequence": ["atom.health.watch", "atom.health.gate", "atom.logos.mercy"],
            "lexicon_meta": {"probe": True},
        },
        session_id="fixture-example-session",
        turn_id=1,
        from_agent="athena_core",
        to_agent="logos_sage",
    )
    ENVELOPE_EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE_EXAMPLE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_doc(env)
    return {"ok": True, "path": str(ENVELOPE_EXAMPLE)}


def write_ko_lexicon_fixture() -> dict:
    doc = {
        "schema": "mkm_inter_agent_ko_health_sidecar_lexicon_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "KO health sidecar lexicon stub for gate/bootstrap only; not production lingua franca.",
        "entries": [
            {"normalized_form": "watch", "atom_id": "atom.health.watch"},
            {"normalized_form": "gate", "atom_id": "atom.health.gate"},
            {"normalized_form": "regime", "atom_id": "atom.health.regime"},
            {"normalized_form": "mercy", "atom_id": "atom.logos.mercy"},
            {"normalized_form": "logos", "atom_id": "atom.logos.core"},
            {"normalized_form": "strong", "atom_id": "atom.morph.strong"},
            {"normalized_form": "morph", "atom_id": "atom.morph.core"},
            {"normalized_form": "greek", "atom_id": "atom.lang.greek"},
            {"normalized_form": "bible", "atom_id": "atom.logos.bible"},
            {"normalized_form": "reference", "atom_id": "atom.meta.reference"},
        ],
    }
    KO_LEXICON.parent.mkdir(parents=True, exist_ok=True)
    KO_LEXICON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(KO_LEXICON), "entry_count": len(doc["entries"])}


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return int(proc.returncode)


def refresh_downstream(*, with_pytest: bool) -> dict:
    steps: list[dict] = []

    def step(name: str, cmd: list[str]) -> None:
        code = _run(cmd)
        steps.append({"step": name, "exit_code": code})

    step("wire_profile", [sys.executable, "scripts/build_mkm_inter_agent_wire_profile_v1.py"])
    step("gloss_enriched", [sys.executable, "scripts/build_mkm_inter_agent_wire_gloss_sidecar_enriched_v1.py"])
    enc_args = [sys.executable, "scripts/build_mkm_inter_agent_encoding_status_v1.py"]
    if not with_pytest:
        enc_args.append("--skip-pytest")
    step("encoding_status", enc_args)
    step("ops_slice", [sys.executable, "scripts/build_mkm_inter_agent_rq019_ops_slice_v1.py"])
    step(
        "regression_chain",
        [sys.executable, "scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py", "--skip-pytest"],
    )
    step("weekly_smoke", [sys.executable, "scripts/build_mkm_inter_agent_rq019_weekly_smoke_readiness_v1.py"])
    step("trackc_slice", [sys.executable, "scripts/build_mkm_inter_agent_trackc_rq019_slice_v1.py"])
    step("closeout", [sys.executable, "scripts/build_mkm_inter_agent_rq019_language_dev_closeout_v1.py"])
    step("encoding_status_final", [sys.executable, "scripts/build_mkm_inter_agent_encoding_status_v1.py"])

    status_path = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
    core_ready = False
    if status_path.is_file():
        st = json.loads(status_path.read_text(encoding="utf-8"))
        core_ready = bool(st.get("rq_019_milestones_core_ready"))
    return {"steps": steps, "rq_019_milestones_core_ready": core_ready}


def main() -> int:
    out: dict = {"schema": "bootstrap_rq019_parallel_gate_v1", "generated_at_utc": _utc()}
    out["fixtures"] = {
        "envelope": write_envelope_fixture(),
        "ko_lexicon": write_ko_lexicon_fixture(),
    }
    out["pass1"] = refresh_downstream(with_pytest=False)
    out["pass2"] = refresh_downstream(with_pytest=True)
    report = ROOT / "reports/bootstrap_rq019_parallel_gate_latest.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report), "core_ready": out["pass2"]["rq_019_milestones_core_ready"]}))
    return 0 if out["pass2"]["rq_019_milestones_core_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
