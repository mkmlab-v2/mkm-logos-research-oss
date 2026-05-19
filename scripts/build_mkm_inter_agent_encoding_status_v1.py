#!/usr/bin/env python3
"""Emit integrated status for MKM Inter-Agent Encoding (RQ-019 milestones M1–M3)."""

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
L1_SPIKE = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_summary_latest.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
V2_TEST = ROOT / "tests" / "test_compression_token_api_v2_stub.py"


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
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(V2_TEST), "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": int(proc.returncode),
        "passed": proc.returncode == 0,
        "test_file": V2_TEST.relative_to(ROOT).as_posix(),
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

        from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{type(exc).__name__}"}

    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
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
    return {
        "ok": True,
        "expand_equals_stub_reconstructed": expanded == recon,
        "jaccard_original_vs_expanded": jac,
        "original_text_on_expand_body": False,
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
    m2_pass = wire_exists
    m3 = _milestone_m3(l1)

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
        "research_only_components": ["l1_side_channel_wire", "l1_inverse_decoder_spike"],
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
