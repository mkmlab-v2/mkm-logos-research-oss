"""Template-catalog wire codec for zone_f_code coding deep pack (B-track PoC).

Bilateral SSOT: receiver holds ``zone_f_code_templates_v1.jsonl`` pinned by catalog_sha256.
Twin axis: token saving on wire vs full snippet; exact_restore via catalog lookup.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

WIRE_SCHEMA = "compression_coding_deep_pack_wire_v1"
_CODE_TOKEN_RE = re.compile(r"\w+|[^\w\s]+", re.UNICODE)


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
    literal_slots: dict[str, str] | None = None,
) -> dict[str, Any]:
    short_hash = catalog_sha256[:8]
    wire: dict[str, Any] = {
        "schema": WIRE_SCHEMA,
        "template_id": template_id,
        "catalog_sha256": catalog_sha256,
        "catalog_sha256_short": short_hash,
        "shard_id": "zone_f_code",
        "sku_class": "mask",
    }
    if literal_slots:
        wire["literal_slots"] = literal_slots
    return wire


def apply_literal_slot_renames(snippet: str, literal_slots: dict[str, str]) -> str:
    """Rename identifiers outside quoted string literals (preserves JSON dict keys)."""
    parts = re.split(r'("(?:[^"\\]|\\.)*")', snippet)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        chunk = part
        for old, new in literal_slots.items():
            chunk = re.sub(rf"\b{re.escape(old)}\b", new, chunk)
        out.append(chunk)
    return "".join(out)


def _tokenize_code(text: str) -> list[str]:
    return _CODE_TOKEN_RE.findall(text)


def extract_literal_slots(canonical: str, variant: str) -> dict[str, str] | None:
    ct = _tokenize_code(canonical)
    vt = _tokenize_code(variant)
    if len(ct) != len(vt):
        return None
    slots: dict[str, str] = {}
    for a, b in zip(ct, vt):
        if a == b:
            continue
        if not (a.isidentifier() and b.isidentifier()):
            return None
        if a in slots and slots[a] != b:
            return None
        slots[a] = b
    if not slots:
        return None
    if apply_literal_slot_renames(canonical, slots) != variant:
        return None
    return slots


def wire_to_compact(wire: dict[str, Any]) -> str:
    """On-wire compact form: bilateral catalog pin + template id (+ optional literal slots)."""
    tid = str(wire["template_id"])
    short_hash = str(wire.get("catalog_sha256_short") or wire["catalog_sha256"][:8])
    base = f"[ZF_MASK:{tid}@{short_hash}"
    slots = wire.get("literal_slots")
    if isinstance(slots, dict) and slots:
        payload = json.dumps(slots, ensure_ascii=False, separators=(",", ":"))
        return f"{base}|{payload}]"
    return f"{base}]"


def wire_to_json(wire: dict[str, Any]) -> str:
    return wire_to_compact(wire)


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
    snippet = str(row["snippet"])
    slots = wire.get("literal_slots")
    if isinstance(slots, dict) and slots:
        snippet = apply_literal_slot_renames(snippet, {str(k): str(v) for k, v in slots.items()})
    return snippet


def _expand_compact_wire(
    compact: str,
    catalog_rows: list[dict[str, Any]],
    *,
    expected_catalog_sha256: str | None = None,
) -> str:
    prefix = "[ZF_MASK:"
    if not compact.startswith(prefix) or not compact.endswith("]"):
        raise ValueError(f"invalid compact wire: {compact!r}")
    body = compact[len(prefix) : -1]
    slots: dict[str, str] | None = None
    if "|" in body:
        body, slots_json = body.rsplit("|", 1)
        parsed = json.loads(slots_json)
        if not isinstance(parsed, dict):
            raise ValueError("literal_slots payload must be object")
        slots = {str(k): str(v) for k, v in parsed.items()}
    if "@" in body:
        template_id, short_hash = body.split("@", 1)
        if expected_catalog_sha256 and not expected_catalog_sha256.startswith(short_hash):
            raise ValueError("catalog short hash mismatch")
    else:
        template_id = body
    row = template_by_id(catalog_rows, template_id)
    if row is None:
        raise KeyError(template_id)
    snippet = str(row["snippet"])
    if slots:
        snippet = apply_literal_slot_renames(snippet, slots)
    return snippet


def match_template_id_by_snippet(text: str, catalog_rows: list[dict[str, Any]]) -> str | None:
    for row in catalog_rows:
        if str(row.get("snippet")) == text:
            return str(row["template_id"])
    return None


def match_template_with_literal_slots(
    text: str,
    catalog_rows: list[dict[str, Any]],
) -> tuple[str, dict[str, str]] | None:
    for row in catalog_rows:
        canonical = str(row.get("snippet") or "")
        slots = extract_literal_slots(canonical, text)
        if slots:
            return str(row["template_id"]), slots
    return None


def resolve_template_match(
    text: str,
    catalog_rows: list[dict[str, Any]],
) -> tuple[str, dict[str, str] | None] | None:
    exact = match_template_id_by_snippet(text, catalog_rows)
    if exact:
        return exact, None
    lit = match_template_with_literal_slots(text, catalog_rows)
    if lit:
        return lit
    return None


DEFAULT_TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "codebook/templates/zone_f_code_templates_v1.jsonl"
DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "codebook/templates/zone_f_code_templates_manifest_v1.json"


def load_default_catalog() -> tuple[list[dict[str, Any]], str]:
    import json as _json

    manifest = _json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = load_template_catalog(DEFAULT_TEMPLATES_PATH)
    return rows, str(manifest["catalog_sha256"])


def measure_template_wire_twin(
    *,
    original_snippet: str,
    template_id: str,
    catalog_sha256: str,
    catalog_rows: list[dict[str, Any]],
    literal_slots: dict[str, str] | None = None,
) -> dict[str, Any]:
    wire = build_wire_packet(
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        literal_slots=literal_slots,
    )
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
        "saving_rate": round(float(saving_rate), 6),
        "exact_restore_ok": exact_restore_ok,
        "jaccard_proxy": round(float(_jaccard(original_snippet, expanded)), 6),
        "wire_compact": wire_compact,
        "wire_token_count": wire_tokens,
        "original_token_count": original_tokens,
        "twin_gate_primary": "saving_rate + exact_restore_ok",
        "jaccard_axis": "separate_from_exact_restore",
    }
