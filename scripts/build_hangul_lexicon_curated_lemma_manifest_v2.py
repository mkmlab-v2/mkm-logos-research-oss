#!/usr/bin/env python3
"""Merge wave1 (29) + wave2 candidates → curated manifest v2 (cap 50, no apply)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
WAVE2 = ROOT / "docs/final/artifacts/hangul_lexicon_wave2_lemma_candidates_v1.json"
OUT = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not V1.is_file() or not WAVE2.is_file():
        print("ABORT: v1 manifest or wave2 candidates missing", file=sys.stderr)
        return 1
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    w2 = json.loads(WAVE2.read_text(encoding="utf-8"))
    lemmas: list[dict] = list(v1.get("lemmas") or [])
    seen = {str(x.get("form", "")).strip() for x in lemmas if x.get("form")}
    for row in w2.get("candidates") or []:
        form = str(row.get("form", "")).strip()
        if not form or form in seen:
            continue
        seen.add(form)
        lemmas.append(
            {
                "form": form,
                "tier": row.get("tier", "D_health_clinical"),
                "source": row.get("source", "wave2_candidate"),
            }
        )
    cap = int(v1.get("max_lemma_count") or 50)
    if len(lemmas) > cap:
        print(f"ABORT: merged count {len(lemmas)} > cap {cap}", file=sys.stderr)
        return 1
    doc = dict(v1)
    doc["schema"] = "hangul_lexicon_curated_ingest_v2"
    doc["generated_at_utc"] = _utc()
    doc["wave"] = 2
    doc["parent_manifest_v1"] = str(V1.relative_to(ROOT)).replace("\\", "/")
    doc["wave2_candidates_source"] = str(WAVE2.relative_to(ROOT)).replace("\\", "/")
    doc["lemmas"] = lemmas
    doc["lemma_count"] = len(lemmas)
    doc["apply_forbidden"] = True
    doc["overlay_output_role_v2"] = (
        "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "lemma_count": len(lemmas)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
