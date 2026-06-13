"""Shared A2A compress pilot helpers (B-track · WATCH)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_MIN_TOKENS = 32
DEFAULT_MAX_EVALUATE_MS_HYPOTHESIS = 615.0
A2A_TARGET_POINTS = Path("docs/final/artifacts/a2a_target_points_v1_latest.json")


def count_tokens(text: str, *, encoding_name: str = "cl100k_base") -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        count = len(enc.encode(text))
        return {"tokens": count, "method": f"tiktoken:{encoding_name}"}
    except Exception as exc:  # noqa: BLE001 — bench fallback only
        est = max(1, len(text) // 4)
        return {
            "tokens": est,
            "method": "char_div_4_estimate",
            "note": f"tiktoken unavailable ({exc})",
        }


def load_compress_skip_rules(root: Path) -> dict[str, Any]:
    path = root / A2A_TARGET_POINTS
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        rules = doc.get("compress_skip_rules_v1")
        if isinstance(rules, dict):
            return rules
    return {
        "status": "default_fallback",
        "min_plaintext_tokens_recommend": DEFAULT_MIN_TOKENS,
        "max_evaluate_report_ms_without_roi_hypothesis": DEFAULT_MAX_EVALUATE_MS_HYPOTHESIS,
    }


def redact_trust_packet(pkt: dict[str, Any], *, max_len: int = 280) -> dict[str, Any]:
    out = json.loads(json.dumps(pkt, ensure_ascii=False))
    if isinstance(out.get("compressed_text"), str) and len(out["compressed_text"]) > max_len:
        out["compressed_text"] = out["compressed_text"][: max_len - 3] + "..."
    stub = (out.get("residual_meta") or {}).get("mk_stub_v2")
    if isinstance(stub, dict) and isinstance(stub.get("reconstructed_text"), str):
        rt = stub["reconstructed_text"]
        if len(rt) > max_len:
            stub["reconstructed_text"] = rt[: max_len - 3] + "..."
    return out


def compress_plaintext_v2(
    client: Any,
    text: str,
    *,
    min_tokens: int,
    routing_profile: str = "track_a_promoted",
    loss_profile: str = "semantic_general",
    client_request_id: str = "a2a-resume-pilot",
    must_keep_overlay_terms: list[str] | None = None,
) -> dict[str, Any]:
    """Compress when token count meets skip threshold; else return skip row."""
    token_row = count_tokens(text)
    token_in = int(token_row["tokens"])
    if token_in < min_tokens:
        return {
            "decision": "skipped_below_min_tokens",
            "token_in": token_in,
            "min_tokens": min_tokens,
            "token_count_method": token_row.get("method"),
            "note": "compress/expand not invoked — ROI unlikely per dialogue mock evidence",
        }

    payload: dict[str, Any] = {
        "text": text,
        "loss_profile": loss_profile,
        "routing_profile": routing_profile,
        "client_request_id": client_request_id,
    }
    if must_keep_overlay_terms:
        payload["must_keep_overlay_terms"] = must_keep_overlay_terms

    cr = client.post("/v2/compress", json=payload)
    body = cr.json() if cr.status_code == 200 else {"error": cr.text}
    packet = body.get("compression_packet") if cr.status_code == 200 else None
    flags = body.get("integrity_flags") or {}
    metrics = body.get("compression_metrics") or {}
    row: dict[str, Any] = {
        "decision": "compressed" if cr.status_code == 200 else "compress_failed",
        "http_status": cr.status_code,
        "token_in": token_in,
        "min_tokens": min_tokens,
        "token_count_method": token_row.get("method"),
        "compression_metrics": metrics,
        "evaluate_report_ms": flags.get("evaluate_report_ms"),
        "routing_profile": routing_profile,
        "loss_profile": loss_profile,
        "content_fingerprint": (packet or {}).get("content_fingerprint"),
        "trust_packet_for_expand": packet if isinstance(packet, dict) else None,
        "trust_packet_redacted": redact_trust_packet(packet) if isinstance(packet, dict) else None,
    }
    if cr.status_code == 200 and isinstance(packet, dict):
        er = client.post("/v2/expand", json={"compression_packet": packet})
        if er.status_code == 200:
            expanded = (er.json() or {}).get("text") or ""
            stub = (packet.get("residual_meta") or {}).get("mk_stub_v2") or {}
            recon = stub.get("reconstructed_text") if isinstance(stub, dict) else None
            row["expand_packet_only"] = {
                "http_status": er.status_code,
                "expand_equals_stub_reconstructed": expanded == recon,
                "expanded_preview_chars": len(expanded),
            }
        else:
            row["expand_packet_only"] = {"http_status": er.status_code, "error": er.text[:200]}
    return row
