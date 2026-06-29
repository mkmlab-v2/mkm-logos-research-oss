#!/usr/bin/env python3
"""ACTIVE candidate re-eval with production 41708 lexicon (v2 · FAIL-COMP-004)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P41708 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"
V2_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_V2_CANDIDATE.json"
MANIFEST_BY_WAVE = {
    "v2_human_6_lemmas": ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2_human.json",
    "v2_pruned_38_lemmas": ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2_pruned.json",
    "v2_50_lemmas": ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json",
}


def main() -> int:
    if not P41708.is_file() or not V2_SIGNOFF.is_file():
        print("ABORT: 41708 lexicon or v2 lexicon signoff missing", file=sys.stderr)
        return 1
    cmd = [
        sys.executable,
        "scripts/build_hangul_curated_active_report_candidate_v1.py",
        "--lexicon-path",
        str(P41708),
        "--out-json",
        str(OUT),
        "--no-require-lexicon-signoff",
    ]
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        return rc
    import json

    doc = json.loads(OUT.read_text(encoding="utf-8"))
    sig = json.loads(V2_SIGNOFF.read_text(encoding="utf-8"))
    wave = str((sig.get("scope") or {}).get("wave") or "v2_pruned_38_lemmas")
    lex_doc = json.loads(P41708.read_text(encoding="utf-8"))
    ko_n = sum(1 for e in lex_doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")
    manifest = MANIFEST_BY_WAVE.get(wave)
    doc["active_profile"]["hangul_curated_v2"] = True
    doc["active_profile"]["lexicon_signoff"] = str(V2_SIGNOFF.relative_to(ROOT)).replace("\\", "/")
    doc["hangul_curated_lineage"] = {
        "schema": "hangul_curated_active_report_candidate_lineage_v2",
        "curated_lemma_manifest": str(manifest.relative_to(ROOT)).replace("\\", "/") if manifest and manifest.is_file() else None,
        "lexicon_row_count": lex_doc.get("row_count"),
        "lemma_count_curated_ko": ko_n,
        "wave": wave,
        "note": f"Production 41708 lexicon re-eval; wave={wave}; not 392 harvest overlay.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = doc.get("compression_metrics") or {}
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "global_token_saving_rate": m.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
