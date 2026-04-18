#!/usr/bin/env python3
"""Load and apply docs/final/artifacts/defense_code_pack_v1.json (국방 코드팩 SSOT).

- Verify linked artifact paths exist
- Scan draft text for forbidden external phrases
- Optional terminology rewrite (대외 초안용; 코드·로그에는 무단 치환 금지)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CODE_PACK = ROOT / "docs" / "final" / "artifacts" / "defense_code_pack_v1.json"


def load_code_pack(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_CODE_PACK
    if not p.is_file():
        raise FileNotFoundError(f"defense code pack missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def verify_linked_artifacts(doc: dict[str, Any], root: Path = ROOT) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    def _add(role: str, rel: str) -> None:
        rel = rel.strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        full = (root / rel).resolve()
        rows.append({"role": role, "path": rel, "exists": full.is_file()})

    for item in doc.get("linked_repo_artifacts") or []:
        _add(str(item.get("role") or "linked"), str(item.get("path") or ""))
    prof = (doc.get("message_profiles") or {}).get("uav_recon_synthetic_v1") or {}
    for key in ("schema_document", "bench_input_artifact"):
        rel = str(prof.get(key) or "").strip()
        if rel:
            _add(f"message_profiles.uav_recon_synthetic_v1.{key}", rel)
    return rows


def scan_forbidden_external_phrases(text: str, doc: dict[str, Any]) -> list[str]:
    forbidden = doc.get("claim_boundaries", {}).get("forbidden_external_phrases") or []
    hits: list[str] = []
    for phrase in forbidden:
        if phrase and phrase in text:
            hits.append(phrase)
    return hits


def terminology_rewrite_draft(text: str, doc: dict[str, Any], locale: str = "ko") -> str:
    """Replace internal labels with defense-facing strings (longest substrings first)."""
    rows = doc.get("terminology_translation_matrix") or []
    pairs: list[tuple[int, str, str]] = []
    val_key = "defense_facing_ko" if locale.lower().startswith("ko") else "defense_facing_en"
    for row in rows:
        key = str(row.get("internal_or_forbidden_in_external") or "")
        val = str(row.get(val_key) or "")
        if not key or not val:
            continue
        for part in (p.strip() for p in key.split("/")):
            if part:
                pairs.append((len(part), part, val))
    pairs.sort(key=lambda x: -x[0])
    out = text
    for _, part, val in pairs:
        out = out.replace(part, val)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Defense code pack v1 loader / checks.")
    ap.add_argument(
        "--code-pack",
        type=Path,
        default=DEFAULT_CODE_PACK,
        help="Path to defense_code_pack_v1.json",
    )
    ap.add_argument("--check", action="store_true", help="Verify linked artifact files exist")
    ap.add_argument("--print-matrix", action="store_true", help="Print terminology rows as JSON")
    ap.add_argument("--scan-text", default="", help="Flag forbidden phrases if present")
    ap.add_argument(
        "--rewrite-draft",
        default="",
        help="Rewrite text using terminology matrix (ko|en via --locale)",
    )
    ap.add_argument("--locale", choices=("ko", "en"), default="ko")
    args = ap.parse_args()

    doc = load_code_pack(args.code_pack)

    if args.check:
        rows = verify_linked_artifacts(doc, ROOT)
        bad = [r for r in rows if not r["exists"]]
        for r in rows:
            status = "OK" if r["exists"] else "MISSING"
            print(f"[{status}] {r['path']}")
        if bad:
            print(f"FAILED: {len(bad)} missing artifact(s)", file=sys.stderr)
            return 2
        print("OK: all referenced artifacts present")
        return 0

    if args.print_matrix:
        print(json.dumps(doc.get("terminology_translation_matrix") or [], ensure_ascii=False, indent=2))
        return 0

    if args.scan_text:
        hits = scan_forbidden_external_phrases(args.scan_text, doc)
        if hits:
            print("FORBIDDEN_HITS:", json.dumps(hits, ensure_ascii=False))
            return 3
        print("OK: no forbidden phrase substring match")
        return 0

    if args.rewrite_draft:
        print(terminology_rewrite_draft(args.rewrite_draft, doc, locale=args.locale))
        return 0

    print("Specify --check, --print-matrix, --scan-text, or --rewrite-draft", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
