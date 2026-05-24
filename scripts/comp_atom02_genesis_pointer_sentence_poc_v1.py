#!/usr/bin/env python3
"""COMP-ATOM-02: full-sentence genesis pointer PoC on V2 bench (research-only)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pointer_hash_snapping_router_v1 import (  # noqa: E402
    _build_lexicon,
    _read_json,
    _route_one,
    _tokenize,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUTS = PILOT / "comp_atom02_router_inputs_full40_v1.json"
RUNTIME = PILOT / "genesis_pointer_runtime_shadow_only_v1.json"
CODEBOOK = PILOT / "genesis_gematria_4d_codebook_lexicon_seed_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_batch(texts: list[str], *, enable_snap: bool) -> tuple[list[dict], Counter[str]]:
    runtime_cfg = _read_json(RUNTIME)
    lexicon = _build_lexicon(_read_json(CODEBOOK))
    rows = []
    oov_counter: Counter[str] = Counter()
    for text in texts:
        row = _route_one(
            text,
            runtime_cfg=runtime_cfg,
            lexicon=lexicon,
            enable_snap=enable_snap,
            snap_ratio=0.74,
            target_path=None,
            memory_v2_oov_passthrough=True,
        )
        rows.append(
            {
                "id_hint": text[:48],
                "token_count": len(_tokenize(text)),
                "pointer_candidate_ok": row["pointer_candidate_ok"],
                "unresolved_count": len(row["unresolved_tokens"]),
                "unresolved_sample": row["unresolved_tokens"][:6],
                "snapped_count": len(row["snap_events"]),
            }
        )
        for t in row["unresolved_tokens"]:
            oov_counter[t] += 1
    return rows, oov_counter


def main() -> int:
    texts = json.loads(INPUTS.read_text(encoding="utf-8"))
    if not isinstance(texts, list):
        print("ABORT: inputs not a list")
        return 1

    no_snap_rows, oov_no = _run_batch(texts, enable_snap=False)
    snap_rows, oov_snap = _run_batch(texts, enable_snap=True)

    ok_no = sum(1 for r in no_snap_rows if r["pointer_candidate_ok"])
    ok_snap = sum(1 for r in snap_rows if r["pointer_candidate_ok"])

    out = {
        "schema": "comp_atom02_genesis_pointer_sentence_poc_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "inputs_path": str(INPUTS.relative_to(ROOT)).replace("\\", "/"),
        "codebook_terms": len(_build_lexicon(_read_json(CODEBOOK))),
        "case_count": len(texts),
        "summary": {
            "pointer_candidate_ok_no_snap": ok_no,
            "pointer_candidate_ok_with_snap": ok_snap,
            "effective_route": "pointer_shadow → track_a_primary (promotion gate off)",
        },
        "top_oov_tokens_no_snap": oov_no.most_common(20),
        "top_oov_tokens_with_snap": oov_snap.most_common(20),
        "per_case_no_snap": no_snap_rows,
        "per_case_with_snap": snap_rows,
        "architecture_note": (
            "pointer_candidate_ok requires every whitespace token in genesis codebook "
            "(74 lexicon-seeded terms). Bench English+punctuation yields chronic OOV; "
            "evaluate_report must_keep uses 41k master_codebook_lexicon_v1, not genesis router."
        ),
        "links": {
            "token_probe_25_ok": "reports/constitution/btrack_pilot/comp_atom02_pointer_router_token_probe_v1.json",
            "lexicon_must_keep": "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json",
            "join_summary": "reports/constitution/btrack_pilot/comp_atom02_join_poc_summary_v1.json",
        },
    }

    path = PILOT / "comp_atom02_genesis_pointer_sentence_poc_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(path), "ok_no_snap": ok_no, "ok_snap": ok_snap, "terms": out["codebook_terms"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
