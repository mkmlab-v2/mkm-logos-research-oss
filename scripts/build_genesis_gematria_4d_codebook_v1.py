#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "genesis_gematria_4d_codebook_v1_latest.json"

DEFAULT_TERMS = [
    "폭락",
    "금화교역",
    "태양인",
    "변동성",
    "레짐",
    "유동성",
    "붕괴",
    "회복",
    "리스크",
    "방어",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_u16_pair(b0: int, b1: int) -> int:
    return (b0 << 8) | b1


def _normalize_u16(v: int) -> float:
    return round(v / 65535.0, 6)


def _build_entry(term: str) -> dict:
    digest = hashlib.sha256(term.encode("utf-8")).digest()
    s = _normalize_u16(_to_u16_pair(digest[0], digest[1]))
    l = _normalize_u16(_to_u16_pair(digest[2], digest[3]))
    k = _normalize_u16(_to_u16_pair(digest[4], digest[5]))
    m = _normalize_u16(_to_u16_pair(digest[6], digest[7]))
    addr = digest[:8].hex()  # 64-bit pointer candidate (hex-encoded)
    return {
        "term": term,
        "address_hash64_hex": addr,
        "vector_4d": {"S": s, "L": l, "K": k, "M": m},
        "hash_algo": "sha256",
    }


def _load_terms(args: argparse.Namespace) -> list[str]:
    if args.terms_json is not None:
        p = args.terms_json if args.terms_json.is_absolute() else ROOT / args.terms_json
        payload = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("terms_json must be a JSON list of strings")
        terms = [str(x).strip() for x in payload if str(x).strip()]
        if not terms:
            raise ValueError("terms_json list is empty")
        return terms
    if args.terms_csv is not None:
        terms = [x.strip() for x in args.terms_csv.split(",") if x.strip()]
        if not terms:
            raise ValueError("terms_csv is empty")
        return terms
    return DEFAULT_TERMS[:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--terms-json", type=Path, default=None, help="JSON file with list[str] terms.")
    ap.add_argument("--terms-csv", type=str, default=None, help="Comma-separated terms.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    terms = _load_terms(args)
    entries = [_build_entry(t) for t in terms]

    # Deterministic reconstruction probe: address hash lookup must recover exact term.
    reverse = {e["address_hash64_hex"]: e["term"] for e in entries}
    exact_ok = 0
    for e in entries:
        exact_ok += int(reverse.get(e["address_hash64_hex"]) == e["term"])

    # Compression estimate (payload-level): compare UTF-8 bytes vs 64-bit pointer vs 4D float32 payload.
    raw_bytes = sum(len(t.encode("utf-8")) for t in terms)
    pointer_bytes = 8 * len(terms)  # 64-bit hash address per term
    vec4_bytes = 16 * len(terms)  # float32 x4 per term

    doc = {
        "schema": "genesis_gematria_4d_codebook_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "term_count": len(terms),
            "terms_source": "terms_json" if args.terms_json else ("terms_csv" if args.terms_csv else "default_terms"),
        },
        "entries": entries,
        "reconstruction_probe": {
            "exact_match_count": exact_ok,
            "exact_match_rate": (exact_ok / float(max(1, len(entries)))),
            "method": "address_hash64_exact_lookup",
        },
        "compression_estimate": {
            "raw_utf8_bytes_total": raw_bytes,
            "pointer_payload_bytes_total": pointer_bytes,
            "vector4_payload_bytes_total": vec4_bytes,
            "pointer_saving_rate": (1.0 - (pointer_bytes / float(max(1, raw_bytes)))),
            "vector4_saving_rate": (1.0 - (vec4_bytes / float(max(1, raw_bytes)))),
        },
        "notes": [
            "Genesis pilot only: 10-term toy codebook.",
            "Exact reconstruction here means dictionary lookup equality, not open-vocabulary semantic restoration.",
            "Do not promote to Track A without collision, sync, and adversarial robustness validation.",
        ],
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "term_count": len(terms)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
