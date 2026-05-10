#!/usr/bin/env python3
"""B-track: joint check — lens music prompt PoC pairs + Logos independent lens evidence_refs.

Citation rule v1 (conservative, deterministic):
  Scan baseline + overlay text for verse-shaped tokens like ``JHN.3.16`` / ``PSA.23.1``.
  Each token must match a verse_id present in the Logos lens ``evidence_refs`` list.
  If none appear, citation_violation is false (Korean-only overlays pass structural bind).

Exit codes:
  0 — citation_violation_rate == 0 and structural_ok
  1 — any violation or structural failure
  2 — bad inputs / missing files
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

VERSE_TOKEN_RE = re.compile(r"\b([A-Z]{2,}\.[0-9]+(?:\.[0-9]+)?)\b")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def _verse_tokens(text: str) -> list[str]:
    return [m.group(1) for m in VERSE_TOKEN_RE.finditer(text or "")]


def _allowed_ids(logos: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    refs = logos.get("evidence_refs")
    if not isinstance(refs, list):
        return out
    for row in refs:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid.strip():
            out.add(vid.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--pairs-jsonl",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "lens_music_prompt_poc_pairs_sample_v1.jsonl",
    )
    ap.add_argument(
        "--logos-lens",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json",
        help="logos_independent_lens_v0 JSON",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "btrack_logos_music_overlay_poc_v1_latest.json",
    )
    args = ap.parse_args()

    if not args.pairs_jsonl.is_file():
        print(f"ERR: pairs-jsonl missing: {args.pairs_jsonl}", flush=True)
        return 2
    if not args.logos_lens.is_file():
        print(f"ERR: logos-lens missing: {args.logos_lens}", flush=True)
        return 2

    try:
        logos = json.loads(args.logos_lens.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"ERR: invalid JSON: {args.logos_lens}", flush=True)
        return 2

    schema_ok = str(logos.get("schema")) == "logos_independent_lens_v0"
    allowed = _allowed_ids(logos)
    structural_ok = schema_ok and len(allowed) >= 1

    rows_out: list[dict[str, Any]] = []
    violations = 0

    for r in _read_jsonl(args.pairs_jsonl):
        pid = r.get("id")
        texts = [
            str(r.get("baseline_response_text") or ""),
            str(r.get("overlay_response_text") or ""),
        ]
        bad_tokens: list[str] = []
        for t in texts:
            for tok in _verse_tokens(t):
                if tok not in allowed:
                    bad_tokens.append(tok)
        viol = len(bad_tokens) > 0
        if viol:
            violations += 1
        rows_out.append(
            {
                "poc_id": pid,
                "citation_violation": viol,
                "unknown_verse_tokens": bad_tokens,
                "verse_tokens_found": [x for t in texts for x in _verse_tokens(t)],
            }
        )

    n = len(rows_out)
    rate = (violations / n) if n else 0.0

    out = {
        "schema": "btrack_logos_music_overlay_poc_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "inputs": {
            "pairs_jsonl": str(args.pairs_jsonl.resolve()),
            "logos_lens": str(args.logos_lens.resolve()),
        },
        "structural_ok": structural_ok,
        "logos_evidence_verse_ids": sorted(allowed),
        "metrics": {
            "rows_total": n,
            "citation_violation_count": violations,
            "citation_violation_rate": round(rate, 6),
        },
        "rows": rows_out,
        "note": "Verse-token scan only (ASCII REF.CH.VS). Korean-only overlays typically have zero tokens.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = structural_ok and rate == 0.0
    print(
        json.dumps(
            {
                "ok": ok,
                "citation_violation_rate": out["metrics"]["citation_violation_rate"],
                "structural_ok": structural_ok,
                "out": str(args.out.resolve()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
