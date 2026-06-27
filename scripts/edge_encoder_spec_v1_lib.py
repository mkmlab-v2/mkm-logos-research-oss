#!/usr/bin/env python3
"""[HYPO] Edge encoder spec — validate coord wire + spec JSON (B-track, FAIL-COMP-004 isolated)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COORD_WIRE_SCHEMA = ROOT / "docs/final/schemas/edge_encoder_coord_wire_v1.schema.json"
SPEC_SCHEMA = ROOT / "docs/final/schemas/edge_encoder_spec_v1.schema.json"
COORD_WIRE_EXAMPLE = ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json"


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_coord_wire_minimal(wire: dict[str, Any]) -> list[str]:
    """Return validation error messages (empty = OK)."""
    errors: list[str] = []
    try:
        jsonschema = __import__("jsonschema")
        schema = _load_schema(COORD_WIRE_SCHEMA)
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(wire), key=lambda e: e.path):
            errors.append(f"coord_wire: {err.message}")
        return errors
    except Exception:
        return _validate_coord_wire_fallback(wire)


def _validate_coord_wire_fallback(wire: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if wire.get("sku_class") != "coord":
        errors.append("coord_wire: sku_class must be coord")
    if wire.get("wire_mode") != "anatomy_overlay_coord_v1":
        errors.append("coord_wire: wire_mode must be anatomy_overlay_coord_v1")
    sha = str(wire.get("base_sha256") or "")
    if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
        errors.append("coord_wire: base_sha256 must be 64-char hex")
    inject = wire.get("coord_inject")
    if not isinstance(inject, dict) or not inject.get("points_norm"):
        errors.append("coord_wire: coord_inject.points_norm required")
    return errors


def validate_edge_encoder_spec(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        jsonschema = __import__("jsonschema")
    except ImportError:
        if doc.get("schema") != "edge_encoder_spec_v1":
            errors.append("spec: schema must be edge_encoder_spec_v1")
        return errors

    schema = _load_schema(SPEC_SCHEMA)
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(doc), key=lambda e: e.path):
        errors.append(f"spec: {err.message}")
    return errors


def load_coord_wire_from_example(
    example_path: Path | None = None,
) -> dict[str, Any]:
    path = (example_path or COORD_WIRE_EXAMPLE).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"missing coord wire example: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    wire = doc.get("coord_wire_minimal")
    if not isinstance(wire, dict):
        raise ValueError("coord_wire_packet_example missing coord_wire_minimal")
    return wire


def check_coord_wire_determinism(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
) -> list[str]:
    """Parse/compact roundtrip + on-disk base SHA256 match."""
    from scripts.coord_anatomy_overlay_wire_v1_lib import (
        compact_coord_wire,
        expand_compact_coord_wire,
        parse_coord_wire_text,
    )
    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    errors: list[str] = []
    wire_json = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    parsed = parse_coord_wire_text(wire_json)
    if parsed is None:
        errors.append("determinism: parse_coord_wire_text failed on canonical JSON")
        return errors

    compact = compact_coord_wire(wire)
    expanded = expand_compact_coord_wire(compact)
    if expanded is None:
        errors.append("determinism: expand_compact_coord_wire failed")
    elif expanded.get("entry_id") != (wire.get("coord_inject") or {}).get("entry_id"):
        errors.append("determinism: compact roundtrip entry_id mismatch")

    asset_id = str(wire.get("base_asset_id") or "")
    if asset_id.startswith("commons:"):
        title = asset_id.split(":", 1)[1]
        fixture_map = {
            "Ninth rib lateral2.png": workspace_root / "data/anatomy/fixtures/ninth_rib_lateral2.png",
            "Second rib lateral2.png": workspace_root / "data/anatomy/fixtures/second_rib_lateral2.png",
        }
        base_path = fixture_map.get(title)
        if base_path and base_path.is_file():
            on_disk = sha256_file(base_path)
            if on_disk != wire.get("base_sha256"):
                errors.append(
                    f"determinism: base_sha256 mismatch fixture {title}"
                )
        else:
            errors.append(f"determinism: fixture missing for {title}")
    return errors


DEFAULT_MASK_CORPUS = (
    ROOT / "data/compression/stateless_poc_prospect_public-open-web-v1_v1.jsonl"
)
MASK_CORPUS_TAG = "public-open-web-v1"
MASK_BACKEND_FALLBACK = "mkm_candidate_pool"
HYBRID_ROUTER_SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"


def expected_mask_backend(*, workspace_root: Path = ROOT) -> str:
    """Resolve public-open-web backend from hybrid router spec SSOT (post-spike sync)."""
    spec_path = workspace_root / HYBRID_ROUTER_SPEC.relative_to(ROOT)
    if not spec_path.is_file():
        return MASK_BACKEND_FALLBACK
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    for row in spec.get("corpus_bindings") or []:
        if not isinstance(row, dict):
            continue
        if row.get("corpus_tag") == MASK_CORPUS_TAG or row.get("corpus_id") == "public_open_web_v1":
            backend = row.get("backend")
            if backend:
                return str(backend)
    return MASK_BACKEND_FALLBACK


def _packet_fingerprint(packet: dict[str, Any]) -> str:
    subset = {
        "compressed_text": packet.get("compressed_text"),
        "router_meta": packet.get("router_meta"),
        "loss_profile": packet.get("loss_profile"),
    }
    return json.dumps(subset, sort_keys=True, ensure_ascii=False)


def _load_mask_cases(corpus: Path, max_cases: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in corpus.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or len(rows) >= max_cases:
            continue
        obj = json.loads(line)
        if isinstance(obj.get("text"), str) and obj["text"].strip():
            rows.append(obj)
    return rows


def check_mask_hybrid_determinism(
    *,
    workspace_root: Path = ROOT,
    corpus_path: Path | None = None,
    max_cases: int = 5,
) -> tuple[list[str], dict[str, Any]]:
    """Edge cache vs server replay: duplicate compress + cached packet expand [HYPO]."""
    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import app

    corpus = (corpus_path or DEFAULT_MASK_CORPUS).resolve()
    if not corpus.is_file():
        return [f"mask_hybrid: missing corpus {corpus}"], {}

    client = TestClient(app)
    cases = _load_mask_cases(corpus, max(1, max_cases))
    if not cases:
        return ["mask_hybrid: no cases loaded"], {}

    errors: list[str] = []
    per_case: list[dict[str, Any]] = []
    backend_expected = expected_mask_backend(workspace_root=workspace_root)

    for obj in cases:
        row_id = str(obj.get("id") or "row")
        row_errors: list[str] = []
        body = {
            "text": obj["text"],
            "loss_profile": "semantic_general",
            "compression_profile": "economy",
            "corpus_tag": MASK_CORPUS_TAG,
            "stateless_packet": True,
            "client_request_id": row_id,
        }
        cr1 = client.post("/v2/compress", json=body)
        cr2 = client.post("/v2/compress", json=body)
        if cr1.status_code != 200 or cr2.status_code != 200:
            row_errors.append(f"compress failed")
            errors.append(f"mask_hybrid: compress failed {row_id}")
            per_case.append({"id": row_id, "ok": False})
            continue

        pkt1 = cr1.json().get("compression_packet") or {}
        pkt2 = cr2.json().get("compression_packet") or {}
        flags1 = cr1.json().get("integrity_flags") or {}
        backend = flags1.get("hybrid_router_backend_recommended")
        if backend != backend_expected:
            row_errors.append(f"backend {backend!r}")
            errors.append(f"mask_hybrid: backend {backend!r} != {backend_expected} for {row_id}")

        fp1 = _packet_fingerprint(pkt1)
        fp2 = _packet_fingerprint(pkt2)
        if fp1 != fp2:
            row_errors.append("fingerprint mismatch")
            errors.append(f"mask_hybrid: compress fingerprint mismatch {row_id}")

        er1 = client.post(
            "/v2/expand",
            json={"compression_packet": pkt1, "decode_mode": "codebook_only"},
        )
        er_cached = client.post(
            "/v2/expand",
            json={"compression_packet": pkt1, "decode_mode": "codebook_only"},
        )
        if er1.status_code != 200 or er_cached.status_code != 200:
            row_errors.append("expand failed")
            errors.append(f"mask_hybrid: expand failed {row_id}")
            per_case.append({"id": row_id, "ok": False})
            continue

        text_a = er1.json().get("text") or ""
        text_b = er_cached.json().get("text") or ""
        if text_a != text_b:
            row_errors.append("cached expand mismatch")
            errors.append(f"mask_hybrid: cached expand mismatch {row_id}")

        per_case.append(
            {
                "id": row_id,
                "ok": not row_errors,
                "backend": backend,
                "fingerprint_stable": fp1 == fp2,
                "cached_expand_stable": text_a == text_b,
            }
        )

    summary = {
        "corpus": str(corpus.relative_to(workspace_root)).replace("\\", "/"),
        "corpus_tag": MASK_CORPUS_TAG,
        "backend_expected": backend_expected,
        "case_count": len(cases),
        "cases": per_case,
    }
    return errors, summary
