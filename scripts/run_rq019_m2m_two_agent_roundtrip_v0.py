#!/usr/bin/env python3
"""Two-agent M2M roundtrip demo — RQ-019 Trust Packet v0.2 (Track B).

Agent A encodes text → Trust Packet v0.2 JSON → Agent B expands.
OOV / codebook pin mismatch / optional allowlist HOLD → empty expand + HOLD signal.

research_only · send_gate HOLD · not multimodal · Domain A allowlist not mutated.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_rq019_trust_packet_v02 import (  # noqa: E402
    DEFAULT_CODEBOOK_ID,
    DEFAULT_CODEBOOK_VERSION,
    build_envelope,
    resolve_hold,
    validate_envelope_shape,
)
from scripts.run_policy_allowlist_hold_gate_v0 import (  # noqa: E402
    DEFAULT_ALLOWLIST,
    evaluate,
    load_allowlist,
)

DEFAULT_OUT = (
    ROOT / "docs/final/artifacts/mkm_rq019_m2m_two_agent_roundtrip_v0_latest.json"
)
DEFAULT_SAMPLE = (
    "내부 에이전트 M2M Trust Packet 라운드트립 스모크 — research_only HOLD."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _get_client():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    return TestClient(app)


def agent_a_encode(
    text: str,
    *,
    codebook_id: str = DEFAULT_CODEBOOK_ID,
    codebook_version: str = DEFAULT_CODEBOOK_VERSION,
    allowlist_ref: str | None = None,
    oov_tokens: list[str] | None = None,
    inject_oov: bool = False,
) -> dict[str, Any]:
    """Agent A: compress via v2 stub → wrap as Trust Packet v0.2 envelope."""
    client = _get_client()
    cr = client.post(
        "/v2/compress",
        json={
            "text": text,
            "loss_profile": "semantic_general",
            "client_request_id": "rq019-m2m-agent-a",
            "stateless_packet": True,
        },
    )
    if cr.status_code != 200:
        raise RuntimeError(f"agent_a compress failed: {cr.status_code} {cr.text}")
    pkt = cr.json()["compression_packet"]
    tokens = list(oov_tokens or [])
    if inject_oov:
        tokens.append("__OOV_UNKNOWN_ATOM_X__")
    return build_envelope(
        pkt,
        codebook_id=codebook_id,
        codebook_version=codebook_version,
        allowlist_ref=allowlist_ref,
        agent_id="agent_a",
        oov_tokens=tokens or None,
    )


def agent_b_expand(
    envelope: dict[str, Any],
    *,
    expected_codebook_id: str = DEFAULT_CODEBOOK_ID,
    expected_codebook_version: str = DEFAULT_CODEBOOK_VERSION,
    policy_query: str | None = None,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    """Agent B: validate → HOLD gate → expand or empty+HOLD."""
    shape_errs = validate_envelope_shape(envelope)
    if shape_errs:
        return {
            "agent_id": "agent_b",
            "text": "",
            "hold_signal": True,
            "hold_decision": {
                "decision": "HOLD",
                "reason_code": "ENVELOPE_SHAPE_INVALID",
                "reason_text": ";".join(shape_errs),
                "research_only": True,
                "send_gate": "HOLD",
            },
            "expanded": False,
            "research_only": True,
            "send_gate": "HOLD",
        }

    policy_hold = None
    if policy_query is not None:
        doc = load_allowlist(allowlist_path or DEFAULT_ALLOWLIST)
        policy_hold = evaluate(doc, policy_query)

    hold = resolve_hold(
        envelope,
        expected_codebook_id=expected_codebook_id,
        expected_codebook_version=expected_codebook_version,
        policy_hold=policy_hold,
    )
    if hold is not None:
        return {
            "agent_id": "agent_b",
            "text": "",
            "hold_signal": True,
            "hold_decision": hold,
            "expanded": False,
            "research_only": True,
            "send_gate": "HOLD",
            "policy_audit": policy_hold,
        }

    client = _get_client()
    pkt = envelope["compression_packet"]
    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    if er.status_code != 200:
        return {
            "agent_id": "agent_b",
            "text": "",
            "hold_signal": True,
            "hold_decision": {
                "decision": "HOLD",
                "reason_code": "EXPAND_HTTP_FAIL",
                "reason_text": f"status={er.status_code}",
                "research_only": True,
                "send_gate": "HOLD",
            },
            "expanded": False,
            "research_only": True,
            "send_gate": "HOLD",
        }
    body = er.json()
    return {
        "agent_id": "agent_b",
        "text": body.get("text") or "",
        "hold_signal": False,
        "hold_decision": {
            "decision": "PASS",
            "reason_code": "ROUNDTRIP_OK",
            "research_only": True,
            "send_gate": "HOLD",
        },
        "expanded": True,
        "integrity_flags": body.get("integrity_flags") or {},
        "research_only": True,
        "send_gate": "HOLD",
        "policy_audit": policy_hold,
    }


def run_roundtrip(
    text: str,
    *,
    inject_oov: bool = False,
    bad_codebook_pin: bool = False,
    policy_query: str | None = None,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    codebook_id = DEFAULT_CODEBOOK_ID
    codebook_version = (
        "BAD_PIN_MISMATCH" if bad_codebook_pin else DEFAULT_CODEBOOK_VERSION
    )
    allowlist_ref = None
    if policy_query is not None:
        allowlist_ref = str((allowlist_path or DEFAULT_ALLOWLIST).as_posix())

    envelope = agent_a_encode(
        text,
        codebook_id=codebook_id,
        codebook_version=codebook_version,
        allowlist_ref=allowlist_ref,
        inject_oov=inject_oov,
    )
    # Agent B always expects the research pin defaults (detects bad pin on A).
    b = agent_b_expand(
        envelope,
        expected_codebook_id=DEFAULT_CODEBOOK_ID,
        expected_codebook_version=DEFAULT_CODEBOOK_VERSION,
        policy_query=policy_query,
        allowlist_path=allowlist_path,
    )
    return {
        "schema": "mkm_rq019_m2m_two_agent_roundtrip_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tag": "[HYPO]",
        "sample_text": text,
        "modes": {
            "inject_oov": inject_oov,
            "bad_codebook_pin": bad_codebook_pin,
            "policy_query": policy_query,
        },
        "envelope": {
            "packet_format_version": envelope.get("packet_format_version"),
            "codebook_id": envelope.get("codebook_id"),
            "codebook_version": envelope.get("codebook_version"),
            "allowlist_ref": envelope.get("allowlist_ref"),
            "oov_tokens": envelope.get("oov_tokens") or [],
            "has_compression_packet": isinstance(
                envelope.get("compression_packet"), dict
            ),
        },
        "agent_b": b,
        "walls": [
            "not_multimodal",
            "not_m2m_100",
            "not_track_c",
            "not_41k_ontology_claim",
            "not_lingua_franca",
            "not_domain_a_b_merged_product",
            "send_gate_HOLD",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text", default=DEFAULT_SAMPLE)
    p.add_argument("--inject-oov", action="store_true")
    p.add_argument("--bad-codebook-pin", action="store_true")
    p.add_argument(
        "--policy-query",
        default=None,
        help="Optional Domain A allowlist compose (HOLD if OOV); does not mutate allowlist.",
    )
    p.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--expect-hold",
        action="store_true",
        help="Exit 0 only if Agent B hold_signal is true",
    )
    p.add_argument(
        "--expect-pass",
        action="store_true",
        help="Exit 0 only if Agent B expanded without HOLD",
    )
    args = p.parse_args(argv)

    result = run_roundtrip(
        args.text,
        inject_oov=args.inject_oov,
        bad_codebook_pin=args.bad_codebook_pin,
        policy_query=args.policy_query,
        allowlist_path=args.allowlist,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    hold = bool((result.get("agent_b") or {}).get("hold_signal"))
    expanded = bool((result.get("agent_b") or {}).get("expanded"))
    ok = True
    if args.expect_hold and not hold:
        ok = False
    if args.expect_pass and (hold or not expanded):
        ok = False

    print(
        json.dumps(
            {
                "ok": ok,
                "hold_signal": hold,
                "expanded": expanded,
                "reason_code": ((result.get("agent_b") or {}).get("hold_decision") or {}).get(
                    "reason_code"
                ),
                "artifact": str(args.out.as_posix()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
