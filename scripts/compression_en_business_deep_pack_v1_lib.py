"""Template-catalog wire codec for zone_h_en_business formal deep pack (B-track PoC).

Wire prefix BIZ_MASK — separate from ZF_MASK (coding) and CS shortcap axis.
Twin axis: token saving on wire vs full snippet; exact_restore via catalog lookup.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

WIRE_SCHEMA = "compression_en_business_deep_pack_wire_v1"
WIRE_PREFIX = "[BIZ_MASK:"
SHARD_ID = "zone_h_en_business_v1"
_TOKEN_RE = re.compile(r"\w+|[^\w\s]+", re.UNICODE)


def _get_encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("o200k_base"), "o200k_base"
    except Exception:
        return None, "utf8_byte_proxy"


def _encode_n(enc: object | None, text: str) -> int:
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text.encode("utf-8")) // 4)


def load_template_catalog(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def template_by_id(rows: list[dict[str, Any]], template_id: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("template_id")) == template_id:
            return row
    return None


def build_wire_packet(
    *,
    template_id: str,
    catalog_sha256: str,
) -> dict[str, Any]:
    short_hash = catalog_sha256[:8]
    return {
        "schema": WIRE_SCHEMA,
        "template_id": template_id,
        "catalog_sha256": catalog_sha256,
        "catalog_sha256_short": short_hash,
        "shard_id": SHARD_ID,
        "sku_class": "mask",
    }


def wire_to_compact(wire: dict[str, Any]) -> str:
    tid = str(wire["template_id"])
    short_hash = str(wire.get("catalog_sha256_short") or wire["catalog_sha256"][:8])
    return f"{WIRE_PREFIX}{tid}@{short_hash}]"


def expand_template_wire(
    wire: dict[str, Any] | str,
    catalog_rows: list[dict[str, Any]],
    *,
    expected_catalog_sha256: str | None = None,
) -> str:
    if isinstance(wire, str):
        return _expand_compact_wire(wire, catalog_rows, expected_catalog_sha256=expected_catalog_sha256)
    if wire.get("schema") != WIRE_SCHEMA:
        raise ValueError(f"unsupported wire schema: {wire.get('schema')}")
    if expected_catalog_sha256 and wire.get("catalog_sha256") != expected_catalog_sha256:
        raise ValueError("catalog_sha256 mismatch")
    template_id = str(wire.get("template_id") or "")
    row = template_by_id(catalog_rows, template_id)
    if row is None:
        raise KeyError(template_id)
    return str(row["snippet"])


def _expand_compact_wire(
    compact: str,
    catalog_rows: list[dict[str, Any]],
    *,
    expected_catalog_sha256: str | None = None,
) -> str:
    if not compact.startswith(WIRE_PREFIX) or not compact.endswith("]"):
        raise ValueError(f"invalid compact wire: {compact!r}")
    body = compact[len(WIRE_PREFIX) : -1]
    if "@" in body:
        template_id, short_hash = body.split("@", 1)
        if expected_catalog_sha256 and not expected_catalog_sha256.startswith(short_hash):
            raise ValueError("catalog short hash mismatch")
    else:
        template_id = body
    row = template_by_id(catalog_rows, template_id)
    if row is None:
        raise KeyError(template_id)
    return str(row["snippet"])


def match_template_id_by_snippet(text: str, catalog_rows: list[dict[str, Any]]) -> str | None:
    for row in catalog_rows:
        if str(row.get("snippet")) == text:
            return str(row["template_id"])
    return None


def resolve_template_match(
    text: str,
    catalog_rows: list[dict[str, Any]],
) -> tuple[str, None] | None:
    exact = match_template_id_by_snippet(text, catalog_rows)
    if exact:
        return exact, None
    return None


def measure_template_wire_twin(
    *,
    original_snippet: str,
    template_id: str,
    catalog_sha256: str,
    catalog_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    wire = build_wire_packet(template_id=template_id, catalog_sha256=catalog_sha256)
    wire_compact = wire_to_compact(wire)
    enc, _ = _get_encoder()
    original_tokens = _encode_n(enc, original_snippet)
    wire_tokens = _encode_n(enc, wire_compact)
    saving_rate = 0.0
    if original_tokens > 0:
        saving_rate = max(0.0, 1.0 - (wire_tokens / original_tokens))
    expanded = expand_template_wire(wire_compact, catalog_rows, expected_catalog_sha256=catalog_sha256)
    exact_restore_ok = expanded == original_snippet
    from scripts.report_multilens_performance_eval import _jaccard

    return {
        "template_id": template_id,
        "ok": True,
        "roundtrip_path": "template_catalog_wire_v1",
        "wire_family": "BIZ_MASK",
        "saving_rate": round(float(saving_rate), 6),
        "exact_restore_ok": exact_restore_ok,
        "jaccard_proxy": round(float(_jaccard(original_snippet, expanded)), 6),
        "wire_compact": wire_compact,
        "wire_token_count": wire_tokens,
        "original_token_count": original_tokens,
        "twin_gate_primary": "saving_rate + exact_restore_ok",
        "jaccard_axis": "separate_from_exact_restore",
    }
