#!/usr/bin/env python3
"""B-track [HYPO]: 41658 + Hangul bench terms (cmp2_011–040 + zone_c) — not production SSOT."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.hangul_lexicon_tokenizer_harness_v1 import zone_c_hangul_overlay_forms  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ZONE_C = ROOT / "codebook" / "shards" / "zone_c_hangul.json"
DEFAULT_OUT = PILOT / "master_codebook_lexicon_v1_41658_hangul_bench_overlay.json"
META_OUT = PILOT / "master_codebook_hangul_bench_overlay_meta_v1_latest.json"
HANGUL_IDS = {f"cmp2_{i:03d}" for i in range(11, 41)}
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_hangul_forms(*, min_len: int = 2, min_freq: int = 1) -> list[str]:
    forms: Counter[str] = Counter()
    for t in zone_c_hangul_overlay_forms():
        if len(t) >= min_len:
            forms[t] += 100
    if INPUT_V2.is_file():
        doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
        for c in doc.get("compression_cases") or []:
            if str(c.get("id", "")) not in HANGUL_IDS:
                continue
            raw = str(c.get("raw_text", ""))
            for w in re.findall(r"\w+", raw, flags=re.UNICODE):
                if _HANGUL_RE.search(w) and len(w) >= min_len:
                    forms[w] += 1
            for syl in _HANGUL_RE.findall(raw):
                if len(syl) >= min_len:
                    forms[syl] += 1
    return [f for f, n in forms.items() if n >= min_freq]


def _ko_entry(form: str) -> dict[str, Any]:
    aid = f"hangul_bench_hypo_v1::{form}"
    return {
        "atom_id": aid,
        "lang": "ko",
        "normalized_form": form,
        "occurrences": 0,
        "lexicon_strongs_candidates": [],
        "lexicon_match_method": "hangul_bench_hypo_v1",
        "morphhb_match_method": "skipped_lang",
        "morphhb_strongs_hints": [],
        "morphhb_chosen": None,
        "morphhb_disambiguation": None,
    }


def build_overlay(
    base_path: Path,
    forms: list[str],
    out_path: Path,
) -> dict[str, Any]:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    by_id = {
        e["atom_id"]: e
        for e in base.get("entries") or []
        if isinstance(e, dict) and e.get("atom_id")
    }
    existing_forms = {
        str(e.get("normalized_form", "")).strip().lower()
        if str(e.get("normalized_form", "")).isascii()
        else str(e.get("normalized_form", "")).strip()
        for e in by_id.values()
    }
    added: list[str] = []
    for form in sorted(set(forms), key=lambda x: (-len(x), x)):
        key = form.lower() if form.isascii() else form
        if key in existing_forms:
            continue
        ent = _ko_entry(form)
        by_id[ent["atom_id"]] = ent
        existing_forms.add(key)
        added.append(ent["atom_id"])
    entries = list(by_id.values())
    payload = dict(base)
    payload["generated_at_utc"] = _utc()
    payload["row_count"] = len(entries)
    payload["entries"] = entries
    payload["overlay_meta"] = {
        "schema": "master_codebook_hangul_bench_overlay_v1",
        "research_only": True,
        "track_a_active_write": False,
        "base": base_path.name,
        "forms_requested_count": len(set(forms)),
        "atom_ids_added": added,
        "atom_ids_added_count": len(added),
        "sources": [
            str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
            str(ZONE_C.relative_to(ROOT)).replace("\\", "/"),
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload["overlay_meta"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Hangul bench lexicon overlay [HYPO]")
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-out", type=Path, default=META_OUT)
    ap.add_argument("--min-token-len", type=int, default=2)
    args = ap.parse_args()

    base = args.base if args.base.is_absolute() else ROOT / args.base
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if not base.is_file():
        print(f"ABORT: missing base {base}")
        return 1

    forms = _collect_hangul_forms(min_len=args.min_token_len)
    meta = build_overlay(base, forms, out)
    meta_doc = {
        "schema": "master_codebook_hangul_bench_overlay_meta_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "overlay_path": str(out.relative_to(ROOT)).replace("\\", "/"),
        **meta,
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "added": meta["atom_ids_added_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
