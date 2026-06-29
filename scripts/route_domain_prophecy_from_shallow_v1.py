#!/usr/bin/env python3
"""Route shallow router domain_tag + text → domain_prophecy registry candidates [B-track]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "data/commander/domain_prophecy_shallow_router_map_v1.json"
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
OUT = ROOT / "reports/domain_prophecy_shallow_route_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def route_candidates(
    shallow_tag: str,
    text: str,
    *,
    map_doc: dict[str, Any],
    registry_doc: dict[str, Any],
    limit: int = 5,
) -> list[dict[str, Any]]:
    tag = str(shallow_tag or "").strip().lower()
    blob = (text or "").lower()
    active = {
        str(r.get("domain_id"))
        for r in (registry_doc.get("domains") or [])
        if isinstance(r, dict) and r.get("status") in ("active", "active_shadow", "active_regression", "active_smoke")
    }
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row in map_doc.get("routes") or []:
        if not isinstance(row, dict):
            continue
        domain_id = str(row.get("domain_id") or "")
        if domain_id not in active:
            continue
        if str(row.get("shallow_domain_tag") or "").lower() != tag:
            continue
        score = 0
        for kw in row.get("keywords") or []:
            if str(kw).lower() in blob:
                score += 2
        scored.append((score, domain_id, row))
    scored.sort(key=lambda t: (-t[0], t[1]))
    out: list[dict[str, Any]] = []
    for score, domain_id, row in scored[:limit]:
        out.append(
            {
                "domain_id": domain_id,
                "shallow_domain_tag": tag,
                "keyword_score": score,
                "keywords": row.get("keywords") or [],
            }
        )
    return out


def self_test() -> list[str]:
    errors: list[str] = []
    if not MAP_PATH.is_file():
        return ["missing router map"]
    map_doc = _load(MAP_PATH)
    registry_doc = _load(REGISTRY) if REGISTRY.is_file() else {"domains": []}
    route_ids = {str(r.get("domain_id")) for r in map_doc.get("routes") or [] if isinstance(r, dict)}
    reg_ids = {str(r.get("domain_id")) for r in registry_doc.get("domains") or [] if isinstance(r, dict)}
    missing = sorted(reg_ids - route_ids)
    extra = sorted(route_ids - reg_ids)
    if missing:
        errors.append(f"registry domains missing from router map: {missing}")
    if extra:
        errors.append(f"router map has unknown domain_ids: {extra}")
    sample = route_candidates("logos", "verse resolution graphrag logos", map_doc=map_doc, registry_doc=registry_doc)
    if not any(c.get("domain_id") == "logos_verse_resolution" for c in sample):
        errors.append("logos sample route failed")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shallow-tag", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if args.self_test:
        errors = self_test()
        ok = not errors
        doc = {
            "schema": "domain_prophecy_shallow_route_self_test_v1",
            "generated_at_utc": _utc(),
            "ok": ok,
            "errors": errors,
            "reproduce": "py scripts/route_domain_prophecy_from_shallow_v1.py --self-test",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": ok, "errors": len(errors)}, ensure_ascii=False))
        return 0 if ok else 1

    if not args.shallow_tag:
        print("FAIL: --shallow-tag required unless --self-test", file=sys.stderr)
        return 2
    map_doc = _load(MAP_PATH)
    registry_doc = _load(REGISTRY)
    candidates = route_candidates(args.shallow_tag, args.text, map_doc=map_doc, registry_doc=registry_doc)
    doc = {
        "schema": "domain_prophecy_shallow_route_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "shallow_domain_tag": args.shallow_tag,
        "input_text": args.text,
        "candidates": candidates,
        "reproduce": f"py scripts/route_domain_prophecy_from_shallow_v1.py --shallow-tag {args.shallow_tag}",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "candidates": len(candidates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
