#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

RUNTIME_CFG_DEFAULT = ART / "genesis_pointer_route_runtime_config_latest.json"
CODEBOOK_DEFAULT = ART / "genesis_gematria_4d_codebook_v1_latest.json"
OUT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash64_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).digest()[:8].hex()


def _tokenize(text: str) -> list[str]:
    return [t for t in text.strip().split() if t]


def _snap_token(tok: str, lexicon_terms: set[str], min_ratio: float = 0.74) -> tuple[str | None, float]:
    if tok in lexicon_terms:
        return tok, 1.0
    cand = difflib.get_close_matches(tok, list(lexicon_terms), n=1, cutoff=min_ratio)
    if not cand:
        return None, 0.0
    c = cand[0]
    return c, difflib.SequenceMatcher(a=tok, b=c).ratio()


def _build_lexicon(codebook_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = codebook_doc.get("entries", [])
    return {str(e.get("term")): e for e in entries if isinstance(e, dict) and e.get("term")}


def _policy_for_path(runtime_cfg: dict[str, Any], target_path: str | None) -> str:
    if not target_path:
        return "unknown"
    fp = runtime_cfg.get("folder_policy", {})
    normalized = target_path.replace("\\", "/").lstrip("./")
    rows = fp.get("rows", [])
    if isinstance(rows, list) and rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            patt = str(row.get("path_pattern", "")).strip()
            pol = str(row.get("policy", "unknown")).strip()
            if not patt:
                continue
            if fnmatch.fnmatch(normalized, patt):
                return pol
    for patt in fp.get("forbid_patterns", []):
        if fnmatch.fnmatch(normalized, str(patt)):
            return "forbid"
    for patt in fp.get("caution_patterns", []):
        if fnmatch.fnmatch(normalized, str(patt)):
            return "caution"
    for patt in fp.get("apply_patterns", []):
        if fnmatch.fnmatch(normalized, str(patt)):
            return "apply"
    return "unknown"


def _route_one(
    text: str,
    *,
    runtime_cfg: dict[str, Any],
    lexicon: dict[str, dict[str, Any]],
    enable_snap: bool,
    snap_ratio: float,
    target_path: str | None,
) -> dict[str, Any]:
    routing = runtime_cfg.get("routing", {})
    route_mode = str(routing.get("route_mode", "track_a_primary"))
    pointer_enabled = bool(routing.get("pointer_enabled", False))
    pointer_shadow = bool(routing.get("pointer_shadow", False))
    path_policy = _policy_for_path(runtime_cfg, target_path)

    toks = _tokenize(text)
    lexicon_terms = set(lexicon.keys())
    resolved: list[str] = []
    snapped: list[dict[str, Any]] = []
    unresolved: list[str] = []

    for tok in toks:
        if tok in lexicon_terms:
            resolved.append(tok)
            continue
        if not enable_snap:
            unresolved.append(tok)
            continue
        snap_tok, ratio = _snap_token(tok, lexicon_terms, min_ratio=snap_ratio)
        if snap_tok is None:
            unresolved.append(tok)
        else:
            resolved.append(snap_tok)
            snapped.append({"from": tok, "to": snap_tok, "ratio": ratio})

    pointer_candidate_ok = len(toks) > 0 and len(unresolved) == 0
    canonical_text = " ".join(resolved) if pointer_candidate_ok else None
    pointer_payload = None
    if pointer_candidate_ok and canonical_text is not None:
        pointer_payload = {
            "address_hash64_hex": _hash64_hex(canonical_text),
            "token_count": len(resolved),
            "snapped_count": len(snapped),
        }

    # Effective path selection:
    # - pointer_primary: use pointer iff candidate_ok, else fallback
    # - pointer_shadow: always keep Track A path, but emit pointer candidate metadata
    # - track_a_primary: always Track A
    if path_policy == "forbid":
        selected_path = "track_a_primary"
        fallback = False
        effective_route_mode = "track_a_primary"
    elif path_policy == "caution":
        # Caution zone is shadow-only unless separately approved.
        selected_path = "track_a_primary"
        fallback = False
        effective_route_mode = "pointer_shadow"
    elif pointer_enabled and route_mode == "pointer_primary" and pointer_candidate_ok:
        selected_path = "pointer_lookup"
        fallback = False
        effective_route_mode = route_mode
    else:
        selected_path = "track_a_primary"
        fallback = pointer_enabled and route_mode == "pointer_primary" and not pointer_candidate_ok
        effective_route_mode = route_mode

    return {
        "input_text": text,
        "route_mode": route_mode,
        "effective_route_mode": effective_route_mode,
        "selected_path": selected_path,
        "pointer_shadow": pointer_shadow,
        "target_path": target_path,
        "path_policy": path_policy,
        "pointer_candidate_ok": pointer_candidate_ok,
        "pointer_payload": pointer_payload,
        "fallback_to_track_a": fallback,
        "unresolved_tokens": unresolved,
        "snap_events": snapped,
    }


def _load_inputs(args: argparse.Namespace) -> list[str]:
    if args.inputs_json is not None:
        p = args.inputs_json if args.inputs_json.is_absolute() else ROOT / args.inputs_json
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("inputs_json must be a JSON list[str]")
        vals = [str(x).strip() for x in data if str(x).strip()]
        if vals:
            return vals
    if args.inputs_csv:
        vals = [x.strip() for x in args.inputs_csv.split(",") if x.strip()]
        if vals:
            return vals
    return [
        "폭락 변동성 리스크 방어",
        "비트코인 시장 공포 확산",
        "금화교역 태양인 회복",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runtime-config", type=Path, default=RUNTIME_CFG_DEFAULT)
    ap.add_argument("--codebook-json", type=Path, default=CODEBOOK_DEFAULT)
    ap.add_argument("--inputs-json", type=Path, default=None)
    ap.add_argument("--inputs-csv", type=str, default=None)
    ap.add_argument("--enable-snap", action="store_true", help="Enable L3-like token snapping for OOV tokens.")
    ap.add_argument("--snap-min-ratio", type=float, default=0.74)
    ap.add_argument("--target-path", type=str, default=None, help="Relative workspace path for folder policy match.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    runtime_path = args.runtime_config if args.runtime_config.is_absolute() else ROOT / args.runtime_config
    codebook_path = args.codebook_json if args.codebook_json.is_absolute() else ROOT / args.codebook_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    runtime_cfg = _read_json(runtime_path)
    codebook_doc = _read_json(codebook_path)
    lexicon = _build_lexicon(codebook_doc)
    inputs = _load_inputs(args)

    rows = [
        _route_one(
            text,
            runtime_cfg=runtime_cfg,
            lexicon=lexicon,
            enable_snap=bool(args.enable_snap),
            snap_ratio=float(args.snap_min_ratio),
            target_path=args.target_path,
        )
        for text in inputs
    ]

    out_doc = {
        "schema": "pointer_hash_snapping_router_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "runtime_config": str(runtime_path),
            "codebook_json": str(codebook_path),
            "input_count": len(inputs),
            "enable_snap": bool(args.enable_snap),
            "snap_min_ratio": float(args.snap_min_ratio),
            "target_path": args.target_path,
        },
        "rows": rows,
        "summary": {
            "pointer_candidate_ok_count": sum(1 for r in rows if r["pointer_candidate_ok"]),
            "selected_pointer_count": sum(1 for r in rows if r["selected_path"] == "pointer_lookup"),
            "selected_track_a_count": sum(1 for r in rows if r["selected_path"] == "track_a_primary"),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "summary": out_doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
