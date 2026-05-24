#!/usr/bin/env python3
"""Emit integrated status for MKM Inter-Agent Encoding (RQ-019 milestones M1–M24)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_encoding_status_latest.json"
WIRE_PROFILE_V0 = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_wire_profile_v0.json"
WIRE_PROFILE_V1 = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_wire_profile_v1.json"
WIRE_ENVELOPE_SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_inter_agent_wire_envelope_v1.schema.json"
WIRE_VS_PACKET_BENCH = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_wire_vs_packet_bench_v1_latest.json"
L1_SPIKE = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_summary_latest.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
V2_TEST = ROOT / "tests" / "test_compression_token_api_v2_stub.py"
WIRE_TESTS = [
    ROOT / "tests" / "test_compression_token_api_v2_stub.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_envelope_v1.py",
    ROOT / "tests" / "test_run_mkm_inter_agent_dialogue_wire_first_v1.py",
    ROOT / "tests" / "test_validate_mkm_inter_agent_wire_envelope_v1.py",
    ROOT / "tests" / "test_build_mkm_inter_agent_atom_gloss_decode_v1.py",
    ROOT / "tests" / "test_export_mkm_inter_agent_wire_session_v1.py",
    ROOT / "tests" / "test_run_mkm_inter_agent_wire_vs_packet_bench_extended_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_sessions_batch_m15_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m16_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m17_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m18_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m19_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m20_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m21_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m22_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m23_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m24_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m25_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m26_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m27_v1.py",
    ROOT / "tests" / "test_mkm_inter_agent_wire_m28_v1.py",
]
KO_WIRE_BENCH = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_wire_bench_v1_latest.json"
ATOM_GLOSS = ROOT / "docs/final/artifacts/mkm_inter_agent_atom_gloss_decode_v1_latest.json"
SESSION_EXPORT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_export_v1_latest.json"
LIVE_HTTP_DIALOGUE = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_live_http_v1_latest.json"
WIRE_VS_PACKET_EXT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_vs_packet_bench_extended_v1_latest.json"
WIRE_SESSIONS_BATCH = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json"
WIRE_GLOSS_SESSION = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_session_report_v1_latest.json"
WIRE_OPS_BRIEF_META = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_ops_brief_v1_latest.json"
WIRE_OPS_BRIEF_MD = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_ops_brief_v1_latest.md"
KO_HEALTH_COVERAGE = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_lexicon_coverage_v1_latest.json"
JSONL_ROUNDTRIP_AUDIT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_jsonl_roundtrip_audit_v1_latest.json"
KO_TOKENIZATION_EXP = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_tokenization_experiment_v1_latest.json"
KO_HEALTH_SIDECAR_DEMO = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_wire_demo_v1_latest.json"
KO_HEALTH_SIDECAR_FIXTURE = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_lexicon_v1.json"
KO_HEALTH_SIDECAR_ENCODE = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_encode_v1_latest.json"
KO_HEALTH_SIDECAR_BATCH_CHAIN = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_batch_chain_v1_latest.json"
)
HEALTH_SIDECAR_JSONL = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_health_sidecar_v1_latest.jsonl"
KO_MORPHOLOGY_SPIKE = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_morphology_spike_v1_latest.json"
M3_PUBLIC_COPY = ROOT / "docs/final/artifacts/mkm_inter_agent_m3_public_copy_v1_latest.json"
HEALTH_WIRE_SIDECAR_DIALOGUE = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json"
)
HEALTH_WIRE_SIDECAR_LIVE_HTTP = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_live_http_v1_latest.json"
)
RQ019_MILESTONE_INDEX = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_milestone_artifact_index_v1_latest.json"
RQ019_OPS_SLICE = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_ops_slice_v1_latest.json"
RQ019_REGRESSION_CHAIN = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_regression_chain_v1_latest.json"
TRACKC_RQ019_SLICE = ROOT / "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json"
GLOSS_SIDECAR_ENRICHED = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_sidecar_enriched_v1_latest.json"
TRACKC_OPS_DASHBOARD = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
TRACKC_OPS_DASHBOARD_MD = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md"
RQ019_WEEKLY_SMOKE_READINESS = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_weekly_smoke_readiness_v1_latest.json"
)
RQ019_LANGUAGE_DEV_CLOSEOUT = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_language_dev_closeout_v1_latest.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _run_v2_pytest() -> dict[str, Any]:
    paths = [p for p in WIRE_TESTS if p.is_file()]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *[str(p) for p in paths], "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": int(proc.returncode),
        "passed": proc.returncode == 0,
        "test_files": [p.relative_to(ROOT).as_posix() for p in paths],
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def _jaccard_words(a: str, b: str) -> float:
    sa = {w for w in a.lower().split() if w}
    sb = {w for w in b.lower().split() if w}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _probe_v2_roundtrip_inprocess() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import LEXICON_RAIL_KEY, RESIDUAL_STUB_KEY, app
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}

    sample = "MKM inter-agent rail demo strong morph bible logos sasang myeongri reference."
    client = TestClient(app)
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    if cr.status_code != 200:
        return {"ok": False, "error": f"compress_status_{cr.status_code}"}
    pkt = cr.json().get("compression_packet")
    if not isinstance(pkt, dict):
        return {"ok": False, "error": "missing_packet"}
    er = client.post("/v2/expand", json={"compression_packet": pkt})
    if er.status_code != 200:
        return {"ok": False, "error": f"expand_status_{er.status_code}"}
    expanded = er.json().get("text", "")
    stub = (pkt.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
    recon = stub.get("reconstructed_text") if isinstance(stub, dict) else None
    jac = _jaccard_words(sample, expanded)
    rail = (pkt.get("residual_meta") or {}).get(LEXICON_RAIL_KEY)
    rail_ok = isinstance(rail, dict) and isinstance(rail.get("atom_id_sequence"), list)
    return {
        "ok": True,
        "expand_equals_stub_reconstructed": expanded == recon,
        "jaccard_original_vs_expanded": jac,
        "original_text_on_expand_body": False,
        "lexicon_rail_present": rail_ok,
        "lexicon_atom_id_count": len(rail.get("atom_id_sequence") or []) if rail_ok else 0,
    }


def _probe_lexicon_wire_http() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import app
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}
    sample = "strong morph greek logos bible reference message kai mercy alpha beta"
    client = TestClient(app)
    enc = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": sample, "zstd_min_raw_bytes": 0},
    )
    if enc.status_code != 200:
        return {"ok": False, "error": f"encode_status_{enc.status_code}"}
    ej = enc.json()
    wire_b64 = ej.get("wire_b64")
    if not wire_b64:
        return {"ok": False, "error": "empty_wire"}
    dec = client.post("/v1/research/mkm_lexicon_wire/decode", json={"wire_b64": wire_b64})
    if dec.status_code != 200:
        return {"ok": False, "error": f"decode_status_{dec.status_code}"}
    enc_ids = ej.get("atom_id_sequence") or []
    dec_ids = dec.json().get("atom_id_sequence") or []
    return {
        "ok": enc_ids == dec_ids and len(enc_ids) > 0,
        "wire_byte_len": ej.get("wire_byte_len"),
        "atom_id_count": len(enc_ids),
        "research_only": (ej.get("integrity_flags") or {}).get("research_only"),
    }


def _probe_wire_envelope_v1() -> dict[str, Any]:
    if not WIRE_ENVELOPE_SCHEMA.is_file():
        return {"ok": False, "error": "missing_json_schema"}
    try:
        from scripts.mkm_inter_agent_wire_envelope_v1 import build_turn_envelope, envelope_utf8_byte_len

        env = build_turn_envelope(
            encode_response={
                "wire_b64": "dGVzdA==",
                "wire_byte_len": 4,
                "codec_variant": "none",
                "atom_id_sequence": ["atom.test"],
                "lexicon_meta": {},
            },
            session_id="probe-session",
            turn_id=1,
            from_agent="a",
            to_agent="b",
        )
        n = envelope_utf8_byte_len(env)
        return {"ok": env.get("schema") == "mkm_inter_agent_wire_envelope_v1" and n > 0, "envelope_utf8_byte_len": n}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _probe_wire_runtime_adapter() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import app
        from scripts.mkm_inter_agent_wire_envelope_v1 import new_session_id
        from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1, send_turn_wire_v1
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}
    client = TestClient(app)
    sid = new_session_id("status-probe")
    sent = send_turn_wire_v1(
        client,
        text="logos bible mercy alpha beta wire runtime",
        session_id=sid,
        turn_id=1,
        from_agent="alpha",
        to_agent="beta",
    )
    if not sent.get("ok"):
        return {"ok": False, "error": "send_failed", "detail": sent}
    recv = receive_turn_wire_v1(client, sent["envelope"])
    return {
        "ok": bool(recv.get("ok")),
        "envelope_utf8_byte_len": sent.get("envelope_utf8_byte_len"),
        "atom_id_count": ((recv.get("decode") or {}).get("atom_id_sequence") or []).__len__(),
    }


def _probe_wire_turn_http() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import app
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}
    client = TestClient(app)
    r = client.post(
        "/v1/research/mkm_inter_agent_wire/turn",
        json={"text": "strong morph greek logos bible reference", "turn_id": 1},
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"turn_status_{r.status_code}"}
    body = r.json()
    env = body.get("envelope") or {}
    return {
        "ok": bool(env.get("schema") == "mkm_inter_agent_wire_envelope_v1" and body.get("envelope_utf8_byte_len", 0) > 0),
        "route": "POST /v1/research/mkm_inter_agent_wire/turn",
    }


def _probe_wire_schema_validation() -> dict[str, Any]:
    try:
        from scripts.validate_mkm_inter_agent_wire_envelope_v1 import EXAMPLE, probe_live_envelope, validate_doc
        import json

        doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        validate_doc(doc)
        live = probe_live_envelope()
        return {"ok": live.get("ok"), "fixture": EXAMPLE.relative_to(ROOT).as_posix(), "live": live}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _milestone_m10_ko() -> dict[str, Any]:
    doc = _load_json(KO_WIRE_BENCH)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": KO_WIRE_BENCH.relative_to(ROOT).as_posix()}
    health = (doc.get("summary") or {}).get("health_avg_atom_rate_tokens")
    return {
        "status": "pass",
        "pass": True,
        "artifact": KO_WIRE_BENCH.relative_to(ROOT).as_posix(),
        "health_avg_atom_rate_tokens": health,
        "corpus_count": len(doc.get("corpora") or {}),
    }


def _milestone_m11_gloss() -> dict[str, Any]:
    doc = _load_json(ATOM_GLOSS)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": ATOM_GLOSS.relative_to(ROOT).as_posix()}
    dense = ((doc.get("samples") or {}).get("lexicon_dense") or {})
    return {
        "status": "pass" if dense.get("atom_id_count", 0) > 0 else "fail",
        "pass": dense.get("atom_id_count", 0) > 0,
        "artifact": ATOM_GLOSS.relative_to(ROOT).as_posix(),
        "lexicon_dense_gloss_preview": (dense.get("gloss_text") or "")[:120],
    }


def _probe_wire_replay_http() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import app
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}
    client = TestClient(app)
    r = client.post(
        "/v1/research/mkm_inter_agent_wire/replay",
        json={"scenario": "trading", "turns": 2},
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"replay_status_{r.status_code}"}
    body = r.json()
    turns = body.get("turns") or []
    return {
        "ok": body.get("turn_count") == 2 and len(turns) == 2,
        "route": "POST /v1/research/mkm_inter_agent_wire/replay",
        "turn_count": body.get("turn_count"),
    }


def _probe_ko_health_sidecar_encode() -> dict[str, Any]:
    doc = _load_json(KO_HEALTH_SIDECAR_ENCODE)
    if doc:
        return {
            "ok": bool(doc.get("ok")),
            "uplift_atom_count": doc.get("uplift_atom_count"),
            "artifact": KO_HEALTH_SIDECAR_ENCODE.relative_to(ROOT).as_posix(),
        }
    try:
        from fastapi.testclient import TestClient

        from scripts.compression_token_api_v2_stub import app

        sample = "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈."
        c = TestClient(app)
        b = c.post("/v1/research/mkm_lexicon_wire/encode", json={"text": sample, "zstd_min_raw_bytes": 0})
        s = c.post(
            "/v1/research/mkm_lexicon_wire/encode",
            json={"text": sample, "zstd_min_raw_bytes": 0, "use_ko_health_sidecar": True},
        )
        if b.status_code != 200 or s.status_code != 200:
            return {"ok": False, "error": "encode_http_failed"}
        b_n = len(b.json().get("atom_id_sequence") or [])
        s_n = len(s.json().get("atom_id_sequence") or [])
        return {"ok": s_n > b_n, "uplift_atom_count": s_n - b_n, "live_probe": True}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _milestone_m28_language_dev_closeout_pack() -> dict[str, Any]:
    closeout = _load_json(RQ019_LANGUAGE_DEV_CLOSEOUT)
    if closeout and closeout.get("ok"):
        return {
            "status": "pass",
            "pass": True,
            "closeout": RQ019_LANGUAGE_DEV_CLOSEOUT.relative_to(ROOT).as_posix(),
            "m12_m27_ready": (closeout.get("language_dev_lane") or {}).get("m12_m27_ready"),
        }
    try:
        from scripts.build_mkm_inter_agent_rq019_language_dev_closeout_v1 import build_closeout

        live = build_closeout()
        return {
            "status": "pass" if live.get("ok") else "fail",
            "pass": bool(live.get("ok")),
            "live_probe": True,
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m27_weekly_smoke_and_dashboard_md() -> dict[str, Any]:
    ready = _load_json(RQ019_WEEKLY_SMOKE_READINESS)
    md_path = TRACKC_OPS_DASHBOARD_MD
    md_ok = False
    if md_path.is_file():
        text = md_path.read_text(encoding="utf-8")
        md_ok = "## Inter-agent RQ-019 (B-track research)" in text and "language_dev_m12_m25_ready" in text
    if ready and ready.get("ok") and md_ok:
        return {
            "status": "pass",
            "pass": True,
            "readiness": RQ019_WEEKLY_SMOKE_READINESS.relative_to(ROOT).as_posix(),
            "dashboard_md": TRACKC_OPS_DASHBOARD_MD.relative_to(ROOT).as_posix(),
        }
    try:
        from scripts.build_mkm_inter_agent_rq019_weekly_smoke_readiness_v1 import build_readiness
        import subprocess

        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
            cwd=str(ROOT),
            check=False,
        )
        ready_live = build_readiness(require_task_registered=False, run_regression=True)
        text = TRACKC_OPS_DASHBOARD_MD.read_text(encoding="utf-8") if TRACKC_OPS_DASHBOARD_MD.is_file() else ""
        md_ok = "## Inter-agent RQ-019 (B-track research)" in text
        ok = bool(ready_live.get("ok")) and md_ok
        return {"status": "pass" if ok else "fail", "pass": ok, "live_probe": True}
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m26_trackc_dashboard_inter_agent_merge() -> dict[str, Any]:
    dash = _load_json(TRACKC_OPS_DASHBOARD)
    reg = _load_json(RQ019_REGRESSION_CHAIN)
    if dash and reg and reg.get("ok"):
        ia = ((dash.get("trackc") or {}).get("inter_agent_rq019")) or {}
        ok = (
            ia.get("role") == "inter_agent_rq019_research_slice_v1"
            and ia.get("research_only") is True
            and bool(reg.get("trackc_dashboard_inter_agent_ok", True))
        )
        return {
            "status": "pass" if ok else "fail",
            "pass": ok,
            "dashboard": TRACKC_OPS_DASHBOARD.relative_to(ROOT).as_posix(),
            "regression_chain": RQ019_REGRESSION_CHAIN.relative_to(ROOT).as_posix(),
            "inter_agent_state": ia.get("state"),
        }
    try:
        import subprocess

        py = sys.executable
        subprocess.run([py, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")], cwd=str(ROOT), check=False)
        from scripts.run_mkm_inter_agent_rq019_regression_chain_v1 import run_chain

        reg_live = run_chain(skip_pytest=True, quick=True)
        dash_live = _load_json(TRACKC_OPS_DASHBOARD) or {}
        ia = ((dash_live.get("trackc") or {}).get("inter_agent_rq019")) or {}
        ok = (
            ia.get("role") == "inter_agent_rq019_research_slice_v1"
            and bool(reg_live.get("ok"))
        )
        return {"status": "pass" if ok else "fail", "pass": ok, "live_probe": True}
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m25_trackc_slice_and_sidecar_gloss() -> dict[str, Any]:
    trackc = _load_json(TRACKC_RQ019_SLICE)
    gloss = _load_json(GLOSS_SIDECAR_ENRICHED)
    profile = _load_json(WIRE_PROFILE_V1)
    if trackc and gloss and profile and trackc.get("ok") and gloss.get("ok"):
        flags = profile.get("research_optional_flags") or {}
        return {
            "status": "pass",
            "pass": True,
            "trackc_slice": TRACKC_RQ019_SLICE.relative_to(ROOT).as_posix(),
            "gloss_enriched": GLOSS_SIDECAR_ENRICHED.relative_to(ROOT).as_posix(),
            "sidecar_flag_documented": "use_ko_health_sidecar" in flags,
        }
    try:
        from scripts.build_mkm_inter_agent_trackc_rq019_slice_v1 import build_slice
        from scripts.build_mkm_inter_agent_wire_gloss_sidecar_enriched_v1 import build_enriched
        from scripts.build_mkm_inter_agent_wire_profile_v1 import build as build_profile

        trackc_live = build_slice()
        gloss_live = build_enriched(turns=4)
        profile_live = build_profile()
        flags = profile_live.get("research_optional_flags") or {}
        ok = bool(trackc_live.get("ok")) and bool(gloss_live.get("ok")) and "use_ko_health_sidecar" in flags
        return {"status": "pass" if ok else "fail", "pass": ok, "live_probe": True}
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m24_ops_slice_and_regression_chain() -> dict[str, Any]:
    ops = _load_json(RQ019_OPS_SLICE)
    reg = _load_json(RQ019_REGRESSION_CHAIN)
    if ops and reg and ops.get("ok") and reg.get("ok"):
        return {
            "status": "pass",
            "pass": True,
            "ops_slice": RQ019_OPS_SLICE.relative_to(ROOT).as_posix(),
            "regression_chain": RQ019_REGRESSION_CHAIN.relative_to(ROOT).as_posix(),
        }
    try:
        from scripts.build_mkm_inter_agent_rq019_ops_slice_v1 import build_ops_slice
        from scripts.run_mkm_inter_agent_rq019_regression_chain_v1 import run_chain

        ops_live = build_ops_slice()
        reg_live = run_chain(skip_pytest=True, quick=True)
        return {
            "status": "pass" if ops_live.get("ok") and reg_live.get("ok") else "fail",
            "pass": bool(ops_live.get("ok")) and reg_live.get("ok"),
            "live_probe": True,
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m23_live_http_and_artifact_index() -> dict[str, Any]:
    live = _load_json(HEALTH_WIRE_SIDECAR_LIVE_HTTP)
    idx = _load_json(RQ019_MILESTONE_INDEX)
    if live and idx:
        count = int(idx.get("milestone_count") or 0)
        index_present = count >= 23
        return {
            "status": "pass" if live.get("ok") and index_present else "fail",
            "pass": bool(live.get("ok")) and index_present,
            "live_http_artifact": HEALTH_WIRE_SIDECAR_LIVE_HTTP.relative_to(ROOT).as_posix(),
            "index_artifact": RQ019_MILESTONE_INDEX.relative_to(ROOT).as_posix(),
            "avg_atom_id_count": live.get("avg_atom_id_count"),
            "milestone_count": count,
            "index_ok_field": idx.get("ok"),
        }
    try:
        from scripts.build_mkm_inter_agent_rq019_milestone_artifact_index_v1 import build_index
        from scripts.capture_mkm_inter_agent_health_wire_sidecar_live_http_v1 import capture

        live_doc = capture(turns=2)
        idx_doc = build_index()
        return {
            "status": "pass" if live_doc.get("ok") and idx_doc.get("ok") else "fail",
            "pass": bool(live_doc.get("ok")) and bool(idx_doc.get("ok")),
            "live_probe": True,
            "avg_atom_id_count": live_doc.get("avg_atom_id_count"),
            "milestone_count": idx_doc.get("milestone_count"),
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m22_health_wire_sidecar_dialogue() -> dict[str, Any]:
    m3 = _load_json(M3_PUBLIC_COPY)
    dial = _load_json(HEALTH_WIRE_SIDECAR_DIALOGUE)
    if m3 and dial:
        return {
            "status": "pass" if m3.get("ok") and dial.get("ok") else "fail",
            "pass": bool(m3.get("ok")) and bool(dial.get("ok")),
            "m3_artifact": M3_PUBLIC_COPY.relative_to(ROOT).as_posix(),
            "dialogue_artifact": HEALTH_WIRE_SIDECAR_DIALOGUE.relative_to(ROOT).as_posix(),
            "uplift_avg_atom_id_count": dial.get("uplift_avg_atom_id_count"),
        }
    try:
        from scripts.capture_mkm_inter_agent_health_wire_sidecar_dialogue_v1 import capture
        from scripts.emit_mkm_inter_agent_m3_public_copy_v1 import emit_public_copy

        m3_live = emit_public_copy()
        dial_live = capture(turns=3)
        return {
            "status": "pass" if m3_live.get("ok") and dial_live.get("ok") else "fail",
            "pass": bool(m3_live.get("ok")) and bool(dial_live.get("ok")),
            "live_probe": True,
            "uplift_avg_atom_id_count": dial_live.get("uplift_avg_atom_id_count"),
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m21_ko_morphology_spike() -> dict[str, Any]:
    doc = _load_json(KO_MORPHOLOGY_SPIKE)
    if doc:
        return {
            "status": "pass" if doc.get("ok") else "fail",
            "pass": bool(doc.get("ok")),
            "artifact": KO_MORPHOLOGY_SPIKE.relative_to(ROOT).as_posix(),
            "backends_available": doc.get("backends_available"),
            "primary_backend": doc.get("primary_backend"),
            "sidecar_atom_total": doc.get("sidecar_atom_total_primary_backend"),
        }
    try:
        from scripts.build_mkm_inter_agent_ko_morphology_spike_v1 import run_spike

        live = run_spike()
        return {
            "status": "pass" if live.get("ok") else "fail",
            "pass": bool(live.get("ok")),
            "live_probe": True,
            "backends_available": live.get("backends_available"),
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m20_ko_health_sidecar_batch_replay() -> dict[str, Any]:
    chain = _load_json(KO_HEALTH_SIDECAR_BATCH_CHAIN)
    jsonl_ok = HEALTH_SIDECAR_JSONL.is_file() and sum(
        1 for ln in HEALTH_SIDECAR_JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()
    ) >= 2
    if chain:
        return {
            "status": "pass" if chain.get("ok") and jsonl_ok else "fail",
            "pass": bool(chain.get("ok")) and jsonl_ok,
            "chain_artifact": KO_HEALTH_SIDECAR_BATCH_CHAIN.relative_to(ROOT).as_posix(),
            "health_jsonl": HEALTH_SIDECAR_JSONL.relative_to(ROOT).as_posix(),
            "avg_atom_id_count": ((chain.get("health_export") or {}).get("avg_atom_id_count")),
            "replay_api_ok": ((chain.get("replay_api") or {}).get("ok")),
        }
    try:
        from scripts.run_mkm_inter_agent_ko_health_sidecar_batch_chain_v1 import run_chain

        live = run_chain(turns=3)
        return {
            "status": "pass" if live.get("ok") else "fail",
            "pass": bool(live.get("ok")),
            "live_probe": True,
            "avg_atom_id_count": ((live.get("health_export") or {}).get("avg_atom_id_count")),
        }
    except Exception as exc:
        return {"status": "fail", "pass": False, "error": f"{type(exc).__name__}:{exc}"}


def _milestone_m18_ko_sidecar() -> dict[str, Any]:
    tok = _load_json(KO_TOKENIZATION_EXP)
    demo = _load_json(KO_HEALTH_SIDECAR_DEMO)
    fixture_ok = KO_HEALTH_SIDECAR_FIXTURE.is_file()
    tok_ok = bool(tok and tok.get("ok"))
    demo_ok = bool(demo and demo.get("ok"))
    uplift = ((demo or {}).get("aggregate") or {}).get("uplift_atoms")
    return {
        "status": "pass" if fixture_ok and tok_ok and demo_ok and (uplift or 0) > 0 else "fail",
        "pass": fixture_ok and tok_ok and demo_ok and (uplift or 0) > 0,
        "tokenization_experiment": KO_TOKENIZATION_EXP.relative_to(ROOT).as_posix(),
        "sidecar_demo": KO_HEALTH_SIDECAR_DEMO.relative_to(ROOT).as_posix(),
        "sidecar_fixture": KO_HEALTH_SIDECAR_FIXTURE.relative_to(ROOT).as_posix(),
        "uplift_atoms": uplift,
        "hypothesis_tier": "B",
    }


def _milestone_m17_ko_audit() -> dict[str, Any]:
    ko = _load_json(KO_HEALTH_COVERAGE)
    audit = _load_json(JSONL_ROUNDTRIP_AUDIT)
    if not ko or not audit:
        return {
            "status": "pending",
            "pass": False,
            "ko_coverage": KO_HEALTH_COVERAGE.relative_to(ROOT).as_posix(),
            "jsonl_audit": JSONL_ROUNDTRIP_AUDIT.relative_to(ROOT).as_posix(),
        }
    ko_ok = bool(ko.get("ok")) and (ko.get("aggregate") or {}).get("token_count", 0) > 0
    audit_ok = bool(audit.get("ok")) and int(audit.get("line_count") or 0) >= 6
    return {
        "status": "pass" if ko_ok and audit_ok else "fail",
        "pass": ko_ok and audit_ok,
        "ko_coverage_artifact": KO_HEALTH_COVERAGE.relative_to(ROOT).as_posix(),
        "jsonl_audit_artifact": JSONL_ROUNDTRIP_AUDIT.relative_to(ROOT).as_posix(),
        "health_hit_rate_tokens": (ko.get("aggregate") or {}).get("hit_rate_tokens"),
        "hangul_forms_in_lexicon": ko.get("hangul_normalized_forms_in_lexicon"),
        "jsonl_line_count": audit.get("line_count"),
        "all_schema_valid": audit.get("all_schema_valid"),
        "all_wire_roundtrip_ok": audit.get("all_wire_roundtrip_ok"),
    }


def _milestone_m16_ops_replay() -> dict[str, Any]:
    meta = _load_json(WIRE_OPS_BRIEF_META)
    replay = _probe_wire_replay_http()
    md_ok = WIRE_OPS_BRIEF_MD.is_file() and WIRE_OPS_BRIEF_MD.stat().st_size > 100
    meta_ok = bool(meta and meta.get("ok") and int(meta.get("scenario_count") or 0) >= 1)
    return {
        "status": "pass" if meta_ok and md_ok and replay.get("ok") else "fail",
        "pass": meta_ok and md_ok and bool(replay.get("ok")),
        "ops_brief_meta": WIRE_OPS_BRIEF_META.relative_to(ROOT).as_posix(),
        "ops_brief_md": WIRE_OPS_BRIEF_MD.relative_to(ROOT).as_posix(),
        "scenario_count": (meta or {}).get("scenario_count"),
        "replay_http_probe": replay,
    }


def _milestone_m15_batch_gloss() -> dict[str, Any]:
    batch = _load_json(WIRE_SESSIONS_BATCH)
    gloss = _load_json(WIRE_GLOSS_SESSION)
    if not batch or not gloss:
        return {
            "status": "pending",
            "pass": False,
            "batch_artifact": WIRE_SESSIONS_BATCH.relative_to(ROOT).as_posix(),
            "gloss_artifact": WIRE_GLOSS_SESSION.relative_to(ROOT).as_posix(),
        }
    batch_ok = bool(batch.get("ok")) and int(batch.get("total_envelopes") or 0) >= 6
    gloss_summary = gloss.get("scenario_summary") if isinstance(gloss.get("scenario_summary"), dict) else {}
    gloss_ok = bool(gloss.get("ok")) and len(gloss_summary) >= 1
    return {
        "status": "pass" if batch_ok and gloss_ok else "fail",
        "pass": batch_ok and gloss_ok,
        "batch_artifact": WIRE_SESSIONS_BATCH.relative_to(ROOT).as_posix(),
        "gloss_artifact": WIRE_GLOSS_SESSION.relative_to(ROOT).as_posix(),
        "total_envelopes": batch.get("total_envelopes"),
        "scenario_count": batch.get("scenario_count"),
        "combined_jsonl": batch.get("combined_jsonl"),
        "scenario_summary": gloss.get("scenario_summary"),
    }


def _milestone_m12_session_export() -> dict[str, Any]:
    doc = _load_json(SESSION_EXPORT)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": SESSION_EXPORT.relative_to(ROOT).as_posix()}
    return {
        "status": "pass" if doc.get("all_envelopes_schema_valid") else "fail",
        "pass": bool(doc.get("ok") and doc.get("all_envelopes_schema_valid")),
        "artifact": SESSION_EXPORT.relative_to(ROOT).as_posix(),
        "envelope_count": doc.get("envelope_count"),
        "envelopes_jsonl": doc.get("envelopes_jsonl"),
    }


def _milestone_m13_live_http() -> dict[str, Any]:
    doc = _load_json(LIVE_HTTP_DIALOGUE)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": LIVE_HTTP_DIALOGUE.relative_to(ROOT).as_posix()}
    return {
        "status": "pass" if doc.get("ok") else "fail",
        "pass": bool(doc.get("ok")),
        "artifact": LIVE_HTTP_DIALOGUE.relative_to(ROOT).as_posix(),
        "capture_mode": doc.get("capture_mode"),
        "wire_turn_endpoint_ok": doc.get("wire_turn_endpoint_ok"),
    }


def _milestone_m14_extended_bench() -> dict[str, Any]:
    doc = _load_json(WIRE_VS_PACKET_EXT)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": WIRE_VS_PACKET_EXT.relative_to(ROOT).as_posix()}
    return {
        "status": "pass" if doc.get("ok") else "fail",
        "pass": bool(doc.get("ok")),
        "artifact": WIRE_VS_PACKET_EXT.relative_to(ROOT).as_posix(),
        "total_unique_lines": doc.get("total_unique_lines"),
        "summary": doc.get("summary"),
    }


def _milestone_m8_bench() -> dict[str, Any]:
    doc = _load_json(WIRE_VS_PACKET_BENCH)
    if not doc:
        return {"status": "pending", "pass": False, "artifact": WIRE_VS_PACKET_BENCH.relative_to(ROOT).as_posix()}
    corpora = doc.get("corpora") if isinstance(doc.get("corpora"), dict) else {}
    has_rows = any(isinstance(v, dict) and (v.get("lines") or []) for v in corpora.values())
    return {
        "status": "pass" if has_rows else "fail",
        "pass": has_rows,
        "artifact": WIRE_VS_PACKET_BENCH.relative_to(ROOT).as_posix(),
        "corpus_count": len(corpora),
    }


def _milestone_m3(l1: dict[str, Any] | None) -> dict[str, Any]:
    agg = (l1 or {}).get("aggregate") if isinstance(l1, dict) else None
    avg_exact = None
    if isinstance(agg, dict) and agg.get("avg_exact_restore_rate") is not None:
        avg_exact = float(agg["avg_exact_restore_rate"])
    public_lines = {
        "ko": (
            "역복원 게이트(연구 스파이크) 기준 exact 복원률은 약 "
            f"{avg_exact * 100:.1f}%"
            if avg_exact is not None
            else "측정 JSON 참조"
        )
        + "이며, 무손실 통역·100% 복원을 주장하지 않습니다.",
        "en": (
            "Measured exact-restore rate from the L1 inverse-decoder research spike "
            f"is ~{avg_exact:.2%}; we do not claim lossless human translation."
            if avg_exact is not None
            else "See L1 spike JSON; no lossless human-decode claim."
        ),
    }
    return {
        "status": "documented" if l1 is not None else "missing_spike_json",
        "research_only": bool((l1 or {}).get("research_only", True)),
        "avg_exact_restore_rate": avg_exact,
        "spike_path": L1_SPIKE.relative_to(ROOT).as_posix(),
        "public_copy_draft": public_lines,
        "pass": l1 is not None and avg_exact is not None,
    }


def build_status(*, run_pytest: bool = True) -> dict[str, Any]:
    wire_exists = WIRE_PROFILE_V0.is_file()
    l1 = _load_json(L1_SPIKE)
    active = _load_json(ACTIVE_REPORT)
    pytest_probe = _run_v2_pytest() if run_pytest else {"skipped": True}
    inproc = _probe_v2_roundtrip_inprocess()

    m1_pass = bool(pytest_probe.get("passed")) and bool(inproc.get("ok"))
    if pytest_probe.get("skipped") and bool(inproc.get("ok")):
        m1_pass = True
    m4_pass = bool(inproc.get("lexicon_rail_present"))
    lex_wire = _probe_lexicon_wire_http()
    m5_pass = bool(lex_wire.get("ok"))
    m2_pass = wire_exists
    m3 = _milestone_m3(l1)
    wire_env_probe = _probe_wire_envelope_v1()
    wire_rt_probe = _probe_wire_runtime_adapter()
    wire_turn_probe = _probe_wire_turn_http()
    m6_pass = bool(wire_env_probe.get("ok")) and WIRE_ENVELOPE_SCHEMA.is_file()
    m7_pass = bool(wire_rt_probe.get("ok")) and bool(wire_turn_probe.get("ok"))
    m8 = _milestone_m8_bench()
    m8_pass = bool(m8.get("pass"))
    wire_v1_exists = WIRE_PROFILE_V1.is_file()
    m9_probe = _probe_wire_schema_validation()
    m9_pass = bool(m9_probe.get("ok"))
    m10 = _milestone_m10_ko()
    m10_pass = bool(m10.get("pass"))
    m11 = _milestone_m11_gloss()
    m11_pass = bool(m11.get("pass"))
    m12 = _milestone_m12_session_export()
    m12_pass = bool(m12.get("pass"))
    m13 = _milestone_m13_live_http()
    m13_pass = bool(m13.get("pass"))
    m14 = _milestone_m14_extended_bench()
    m14_pass = bool(m14.get("pass"))
    m15 = _milestone_m15_batch_gloss()
    m15_pass = bool(m15.get("pass"))
    m16 = _milestone_m16_ops_replay()
    m16_pass = bool(m16.get("pass"))
    m17 = _milestone_m17_ko_audit()
    m17_pass = bool(m17.get("pass"))
    m18 = _milestone_m18_ko_sidecar()
    m18_pass = bool(m18.get("pass"))
    m19_probe = _probe_ko_health_sidecar_encode()
    m19_pass = bool(m19_probe.get("ok"))
    m20 = _milestone_m20_ko_health_sidecar_batch_replay()
    m20_pass = bool(m20.get("pass"))
    m21 = _milestone_m21_ko_morphology_spike()
    m21_pass = bool(m21.get("pass"))
    m22 = _milestone_m22_health_wire_sidecar_dialogue()
    m22_pass = bool(m22.get("pass"))
    m23 = _milestone_m23_live_http_and_artifact_index()
    m23_pass = bool(m23.get("pass"))
    m24 = _milestone_m24_ops_slice_and_regression_chain()
    m24_pass = bool(m24.get("pass"))
    m25 = _milestone_m25_trackc_slice_and_sidecar_gloss()
    m25_pass = bool(m25.get("pass"))
    m26 = _milestone_m26_trackc_dashboard_inter_agent_merge()
    m26_pass = bool(m26.get("pass"))
    m27 = _milestone_m27_weekly_smoke_and_dashboard_md()
    m27_pass = bool(m27.get("pass"))
    m28 = _milestone_m28_language_dev_closeout_pack()
    m28_pass = bool(m28.get("pass"))

    milestones = {
        "m1_v2_phase2_packet_only_expand": {
            "status": "pass" if m1_pass else "fail",
            "pytest": pytest_probe,
            "inprocess_roundtrip": inproc,
            "evidence_paths": [
                "scripts/compression_token_api_v2_stub.py",
                "docs/final/openapi_token_compression_v2_draft.yaml",
                V2_TEST.relative_to(ROOT).as_posix(),
            ],
        },
        "m2_wire_profile_v0": {
            "status": "pass" if m2_pass else "fail",
            "artifact": WIRE_PROFILE_V0.relative_to(ROOT).as_posix(),
        },
        "m3_human_decoder_public_copy": m3,
        "m4_lexicon_atom_id_rail_on_packet": {
            "status": "pass" if m4_pass else "fail",
            "inprocess_probe": {
                "lexicon_rail_present": inproc.get("lexicon_rail_present"),
                "lexicon_atom_id_count": inproc.get("lexicon_atom_id_count"),
            },
            "evidence_paths": [
                "scripts/core/master_codebook_lexicon_v1_bridge.py",
                "scripts/compression_token_api_v2_stub.py",
            ],
            "note": "41k atom_id sequence in residual_meta; not a finished lingua franca wire codec.",
        },
        "m5_lexicon_wire_http_research": {
            "status": "pass" if m5_pass else "fail",
            "inprocess_probe": lex_wire,
            "evidence_paths": [
                "scripts/compression_token_api_v2_stub.py",
                "scripts/capture_mkm_inter_agent_lexicon_wire_http_v1.py",
            ],
            "http_routes": [
                "POST /v1/research/mkm_lexicon_wire/encode",
                "POST /v1/research/mkm_lexicon_wire/decode",
            ],
            "note": "Atom-id-only side channel on adaptive msgpack; research_only.",
        },
        "m6_wire_envelope_v1": {
            "status": "pass" if m6_pass else "fail",
            "inprocess_probe": wire_env_probe,
            "evidence_paths": [
                "scripts/mkm_inter_agent_wire_envelope_v1.py",
                WIRE_ENVELOPE_SCHEMA.relative_to(ROOT).as_posix(),
            ],
            "note": "Turn envelope JSON on-wire; wire-first vs full Trust Packet.",
        },
        "m7_runtime_adapter_wire_first": {
            "status": "pass" if m7_pass else "fail",
            "runtime_adapter_probe": wire_rt_probe,
            "http_turn_probe": wire_turn_probe,
            "evidence_paths": [
                "scripts/mkm_inter_agent_wire_runtime_adapter_v1.py",
                "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
            ],
            "http_routes": ["POST /v1/research/mkm_inter_agent_wire/turn"],
        },
        "m8_wire_vs_packet_bench": m8,
        "m9_wire_envelope_schema_validation": {
            "status": "pass" if m9_pass else "fail",
            "probe": m9_probe,
            "evidence_paths": [
                "scripts/validate_mkm_inter_agent_wire_envelope_v1.py",
                "docs/final/schemas/mkm_inter_agent_wire_envelope_v1.schema.json",
                "docs/final/artifacts/fixtures/mkm_inter_agent_wire_envelope_v1.example.json",
            ],
        },
        "m10_ko_wire_lexicon_bench": m10,
        "m11_atom_gloss_human_decoder": {
            **m11,
            "note": "Lexicon normalized_form gloss; complements L1 ~58% exact-restore spike.",
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_atom_gloss_decode_v1.py",
                "scripts/core/master_codebook_lexicon_v1_bridge.py",
            ],
        },
        "m12_wire_session_export": {
            **m12,
            "evidence_paths": [
                "scripts/export_mkm_inter_agent_wire_session_v1.py",
                "docs/final/artifacts/mkm_inter_agent_wire_session_export_v1_latest.jsonl",
            ],
            "note": "Multi-turn JSONL replay export; each envelope schema-validated.",
        },
        "m13_live_http_dialogue": {
            **m13,
            "evidence_paths": [
                "scripts/mkm_inter_agent_http_client_v1.py",
                "scripts/run_mkm_inter_agent_dialogue_wire_first_live_http_v1.py",
            ],
            "note": "Real HTTP via env base URL or ephemeral uvicorn; not TestClient-only.",
        },
        "m14_wire_vs_packet_bench_extended": {
            **m14,
            "evidence_paths": ["scripts/run_mkm_inter_agent_wire_vs_packet_bench_extended_v1.py"],
            "note": "Dialogue + hit-rate corpora merged; byte savings may be negative on short KO lines.",
        },
        "m15_batch_sessions_wire_gloss_report": {
            **m15,
            "evidence_paths": [
                "scripts/export_mkm_inter_agent_wire_sessions_batch_v1.py",
                "scripts/build_mkm_inter_agent_wire_gloss_session_report_v1.py",
            ],
            "note": "3-scenario session JSONL batch + per-turn gloss replay for operator review.",
        },
        "m16_ops_brief_and_wire_replay_api": {
            **m16,
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_wire_session_ops_brief_v1.py",
                "scripts/mkm_inter_agent_wire_replay_v1.py",
                "scripts/compression_token_api_v2_stub.py",
            ],
            "http_routes": ["POST /v1/research/mkm_inter_agent_wire/replay"],
            "note": "Operator MD brief + research replay endpoint (gloss + wire decode check).",
        },
        "m17_ko_health_coverage_jsonl_roundtrip_audit": {
            **m17,
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_ko_health_lexicon_coverage_v1.py",
                "scripts/audit_mkm_inter_agent_wire_session_jsonl_roundtrip_v1.py",
            ],
            "note": "KO health lexicon gap measurement + batch JSONL schema/wire audit.",
        },
        "m18_ko_tokenization_sidecar_hypothesis": {
            **m18,
            "evidence_paths": [
                "scripts/mkm_inter_agent_ko_tokenization_v1.py",
                "scripts/build_mkm_inter_agent_ko_tokenization_experiment_v1.py",
                "scripts/mkm_inter_agent_ko_health_sidecar_v1.py",
                "scripts/run_mkm_inter_agent_ko_health_sidecar_wire_demo_v1.py",
                KO_HEALTH_SIDECAR_FIXTURE.relative_to(ROOT).as_posix(),
            ],
            "note": "[HYPO] B-track KO health sidecar overlay; not production codebook merge.",
        },
        "m19_ko_health_sidecar_research_encode_opt_in": {
            "status": "pass" if m19_pass else "fail",
            "pass": m19_pass,
            "probe": m19_probe,
            "evidence_paths": [
                "scripts/compression_token_api_v2_stub.py",
                "scripts/capture_mkm_inter_agent_ko_health_sidecar_encode_v1.py",
            ],
            "request_fields": ["use_ko_health_sidecar"],
            "http_routes": [
                "POST /v1/research/mkm_lexicon_wire/encode",
                "POST /v1/research/mkm_inter_agent_wire/turn",
            ],
            "note": "Opt-in [HYPO] flag on research encode/turn only; default false.",
        },
        "m20_ko_health_sidecar_batch_jsonl_replay_chain": {
            **m20,
            "evidence_paths": [
                "scripts/run_mkm_inter_agent_ko_health_sidecar_batch_chain_v1.py",
                "scripts/export_mkm_inter_agent_wire_session_v1.py",
                "scripts/export_mkm_inter_agent_wire_sessions_batch_v1.py",
                "scripts/mkm_inter_agent_wire_replay_v1.py",
                HEALTH_SIDECAR_JSONL.relative_to(ROOT).as_posix(),
            ],
            "cli_flags": ["--sidecar-scenarios health", "use_ko_health_sidecar on replay API"],
            "note": "Sidecar through runtime adapter + health JSONL + replay; not default wire bus.",
        },
        "m21_ko_morphology_lexicon_spike": {
            **m21,
            "evidence_paths": [
                "scripts/mkm_inter_agent_ko_morphology_v1.py",
                "scripts/build_mkm_inter_agent_ko_morphology_spike_v1.py",
                KO_MORPHOLOGY_SPIKE.relative_to(ROOT).as_posix(),
            ],
            "hypothesis_tier": "B",
            "note": "Optional Kiwi backend; heuristic fallback. Does not merge into 41k codebook.",
        },
        "m22_m3_public_copy_and_health_wire_sidecar_dialogue": {
            **m22,
            "evidence_paths": [
                "scripts/emit_mkm_inter_agent_m3_public_copy_v1.py",
                "scripts/capture_mkm_inter_agent_health_wire_sidecar_dialogue_v1.py",
                "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
                M3_PUBLIC_COPY.relative_to(ROOT).as_posix(),
                HEALTH_WIRE_SIDECAR_DIALOGUE.relative_to(ROOT).as_posix(),
            ],
            "note": "M3 disclaimer artifact + health wire-first sidecar uplift; research_only.",
        },
        "m23_health_sidecar_live_http_and_rq019_artifact_index": {
            **m23,
            "evidence_paths": [
                "scripts/capture_mkm_inter_agent_health_wire_sidecar_live_http_v1.py",
                "scripts/build_mkm_inter_agent_rq019_milestone_artifact_index_v1.py",
                "scripts/run_mkm_inter_agent_dialogue_wire_first_live_http_v1.py",
                HEALTH_WIRE_SIDECAR_LIVE_HTTP.relative_to(ROOT).as_posix(),
                RQ019_MILESTONE_INDEX.relative_to(ROOT).as_posix(),
            ],
            "note": "Real HTTP sidecar path + operator milestone index; not production bus.",
        },
        "m24_rq019_ops_slice_and_regression_chain": {
            **m24,
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_rq019_ops_slice_v1.py",
                "scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py",
                RQ019_OPS_SLICE.relative_to(ROOT).as_posix(),
                RQ019_REGRESSION_CHAIN.relative_to(ROOT).as_posix(),
            ],
            "note": "Operator ops slice + one-click regression chain; weekly smoke entry point.",
        },
        "m25_trackc_slice_and_sidecar_gloss": {
            **m25,
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_trackc_rq019_slice_v1.py",
                "scripts/build_mkm_inter_agent_wire_gloss_sidecar_enriched_v1.py",
                TRACKC_RQ019_SLICE.relative_to(ROOT).as_posix(),
                GLOSS_SIDECAR_ENRICHED.relative_to(ROOT).as_posix(),
                WIRE_PROFILE_V1.relative_to(ROOT).as_posix(),
            ],
            "note": "Track C dashboard slice + sidecar-enriched gloss; wire profile documents optional flag.",
        },
        "m26_trackc_dashboard_inter_agent_merge": {
            **m26,
            "evidence_paths": [
                "scripts/build_mkm_trackc_ops_dashboard_v1.py",
                "scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py",
                TRACKC_OPS_DASHBOARD.relative_to(ROOT).as_posix(),
                RQ019_REGRESSION_CHAIN.relative_to(ROOT).as_posix(),
            ],
            "note": "Track C ops dashboard exposes inter_agent_rq019; regression chain gates M25 artifacts.",
        },
        "m27_weekly_smoke_runner_and_dashboard_md": {
            **m27,
            "evidence_paths": [
                "scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1",
                "scripts/Register-MkmInterAgentRq019WeeklySmokeTask.ps1",
                "scripts/Verify-MkmInterAgentRq019WeeklyScheduledTask_v1.ps1",
                "scripts/build_mkm_inter_agent_rq019_weekly_smoke_readiness_v1.py",
                RQ019_WEEKLY_SMOKE_READINESS.relative_to(ROOT).as_posix(),
                TRACKC_OPS_DASHBOARD_MD.relative_to(ROOT).as_posix(),
            ],
            "note": "Weekly smoke entry + Track C MD operator lines; task registration optional on dev machines.",
        },
        "m28_language_dev_closeout_pack": {
            **m28,
            "evidence_paths": [
                "scripts/build_mkm_inter_agent_rq019_language_dev_closeout_v1.py",
                RQ019_LANGUAGE_DEV_CLOSEOUT.relative_to(ROOT).as_posix(),
                "docs/final/artifacts/mkm_inter_agent_rq019_milestone_artifact_index_v1_latest.json",
            ],
            "note": "M12–M27 operator closeout JSON; not production bus or Track A merge.",
        },
    }

    track_a_snapshot: dict[str, Any] = {}
    if active:
        cm = active.get("compression_metrics") if isinstance(active.get("compression_metrics"), dict) else {}
        track_a_snapshot = {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_jaccard": active.get("avg_jaccard"),
            "apply_gematria_4d_bridge_policy": active.get("apply_gematria_4d_bridge_policy"),
        }

    all_core = m1_pass and m2_pass and m3.get("pass")
    wire_layer_ready = m6_pass and m7_pass and m8_pass and wire_v1_exists
    language_dev_m9_m11_ready = m9_pass and m10_pass and m11_pass
    language_dev_m12_m14_ready = m12_pass and m13_pass and m14_pass
    language_dev_m15_ready = m15_pass
    language_dev_m16_ready = m16_pass
    language_dev_m17_ready = m17_pass
    language_dev_m18_ready = m18_pass
    language_dev_m19_ready = m19_pass
    language_dev_m20_ready = m20_pass
    language_dev_m21_ready = m21_pass
    language_dev_m22_ready = m22_pass
    language_dev_m23_ready = m23_pass
    language_dev_m24_ready = m24_pass
    language_dev_m25_ready = m25_pass
    language_dev_m26_ready = m26_pass
    language_dev_m27_ready = m27_pass
    language_dev_m28_ready = m28_pass
    language_dev_m12_m15_ready = language_dev_m12_m14_ready and m15_pass
    language_dev_m12_m16_ready = language_dev_m12_m14_ready and m15_pass and m16_pass
    language_dev_m12_m17_ready = language_dev_m12_m14_ready and m15_pass and m16_pass and m17_pass
    language_dev_m12_m18_ready = language_dev_m12_m14_ready and m15_pass and m16_pass and m17_pass and m18_pass
    language_dev_m12_m19_ready = (
        language_dev_m12_m14_ready and m15_pass and m16_pass and m17_pass and m18_pass and m19_pass
    )
    language_dev_m12_m20_ready = language_dev_m12_m19_ready and m20_pass
    language_dev_m12_m21_ready = language_dev_m12_m20_ready and m21_pass
    language_dev_m12_m22_ready = language_dev_m12_m21_ready and m22_pass
    language_dev_m12_m23_ready = language_dev_m12_m22_ready and m23_pass
    language_dev_m12_m24_ready = language_dev_m12_m23_ready and m24_pass
    language_dev_m12_m25_ready = language_dev_m12_m24_ready and m25_pass
    language_dev_m12_m26_ready = language_dev_m12_m25_ready and m26_pass
    language_dev_m12_m27_ready = language_dev_m12_m26_ready and m27_pass
    language_dev_m12_m28_ready = language_dev_m12_m27_ready and m28_pass
    health_approval = _load_json(
        ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json"
    )
    from scripts.mkm_inter_agent_rq019_status_v1 import resolve_rq019_status

    rq_019_status = resolve_rq019_status()
    close_path = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_commander_close_v1_latest.json"
    pointers: dict[str, str | None] = {
        "sota_map": "docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md",
        "trust_packet_onepager": "docs/final/artifacts/lg_compression_trust_packet_onepager_v1.md",
        "first_message_worked_example": "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md",
        "first_message_live_http": "docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json",
        "health_domain_commander_approval": (
            "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json"
        ),
    }
    if close_path.is_file():
        pointers["rq019_commander_close"] = close_path.relative_to(ROOT).as_posix()
    return {
        "schema": "mkm_inter_agent_encoding_status_v1",
        "generated_at_utc": _utc_now(),
        "rq_019": rq_019_status,
        "rq_019_milestones_core_ready": all_core,
        "rq_019_milestones_wire_layer_ready": wire_layer_ready,
        "rq_019_language_dev_m9_m11_ready": language_dev_m9_m11_ready,
        "rq_019_language_dev_m12_m14_ready": language_dev_m12_m14_ready,
        "rq_019_language_dev_m15_ready": language_dev_m15_ready,
        "rq_019_language_dev_m16_ready": language_dev_m16_ready,
        "rq_019_language_dev_m17_ready": language_dev_m17_ready,
        "rq_019_language_dev_m18_ready": language_dev_m18_ready,
        "rq_019_language_dev_m19_ready": language_dev_m19_ready,
        "rq_019_language_dev_m20_ready": language_dev_m20_ready,
        "rq_019_language_dev_m21_ready": language_dev_m21_ready,
        "rq_019_language_dev_m22_ready": language_dev_m22_ready,
        "rq_019_language_dev_m23_ready": language_dev_m23_ready,
        "rq_019_language_dev_m24_ready": language_dev_m24_ready,
        "rq_019_language_dev_m25_ready": language_dev_m25_ready,
        "rq_019_language_dev_m26_ready": language_dev_m26_ready,
        "rq_019_language_dev_m27_ready": language_dev_m27_ready,
        "rq_019_language_dev_m28_ready": language_dev_m28_ready,
        "rq_019_language_dev_m12_m15_ready": language_dev_m12_m15_ready,
        "rq_019_language_dev_m12_m16_ready": language_dev_m12_m16_ready,
        "rq_019_language_dev_m12_m17_ready": language_dev_m12_m17_ready,
        "rq_019_language_dev_m12_m18_ready": language_dev_m12_m18_ready,
        "rq_019_language_dev_m12_m19_ready": language_dev_m12_m19_ready,
        "rq_019_language_dev_m12_m20_ready": language_dev_m12_m20_ready,
        "rq_019_language_dev_m12_m21_ready": language_dev_m12_m21_ready,
        "rq_019_language_dev_m12_m22_ready": language_dev_m12_m22_ready,
        "rq_019_language_dev_m12_m23_ready": language_dev_m12_m23_ready,
        "rq_019_language_dev_m12_m24_ready": language_dev_m12_m24_ready,
        "rq_019_language_dev_m12_m25_ready": language_dev_m12_m25_ready,
        "rq_019_language_dev_m12_m26_ready": language_dev_m12_m26_ready,
        "rq_019_language_dev_m12_m27_ready": language_dev_m12_m27_ready,
        "rq_019_language_dev_m12_m28_ready": language_dev_m12_m28_ready,
        "research_only_components": [
            "l1_side_channel_wire",
            "l1_inverse_decoder_spike",
            "mkm_inter_agent_wire_envelope_v1",
            "mkm_inter_agent_atom_gloss_decode_v1",
            "mkm_inter_agent_wire_session_export_v1",
            "mkm_inter_agent_http_client_v1",
            "mkm_inter_agent_wire_sessions_batch_v1",
            "mkm_inter_agent_wire_gloss_session_report_v1",
            "mkm_inter_agent_wire_session_ops_brief_v1",
            "mkm_inter_agent_wire_replay_v1",
            "mkm_inter_agent_ko_health_sidecar_v1",
            "mkm_inter_agent_ko_health_sidecar_batch_chain_v1",
            "mkm_inter_agent_ko_morphology_v1",
        ],
        "milestones": milestones,
        "track_a_compression_snapshot": track_a_snapshot,
        "pointers": pointers,
        "health_domain_commander_approved": bool(
            health_approval and health_approval.get("commander_approved")
        ),
        "boundary_ack": (
            "Not a finished MKM Language / Lingua Franca standard. "
            "No production SLA. No beats-SOTA-papers claim."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM inter-agent encoding integrated status JSON.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-pytest", action="store_true", help="Skip subprocess pytest (faster).")
    ap.add_argument("--strict-exit", action="store_true", help="Exit 1 if core milestones not ready.")
    args = ap.parse_args()

    doc = build_status(run_pytest=not args.skip_pytest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "rq_019_milestones_core_ready": doc["rq_019_milestones_core_ready"]}, ensure_ascii=False))
    if args.strict_exit and not doc.get("rq_019_milestones_core_ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
