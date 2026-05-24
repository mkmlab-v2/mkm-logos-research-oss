#!/usr/bin/env python3
"""M21: KO morphology spike vs 41k lexicon + sidecar uplift (research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_morphology_spike_v1_latest.json"

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import ALPHA_LINES_HEALTH, BETA_LINES_HEALTH  # noqa: E402
from scripts.mkm_inter_agent_ko_morphology_v1 import available_backends, morph_tokenize  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lexicon_hit_rate(tokens: list[str], path: Path) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import _load_lexicon_index

    forms, _ = _load_lexicon_index(str(path.resolve()))
    unique = list(dict.fromkeys(tokens))
    hits = [t for t in unique if t.lower() in forms or t in forms]
    return {
        "token_count": len(unique),
        "hit_count": len(hits),
        "hit_rate": round(len(hits) / len(unique), 6) if unique else None,
    }


def run_spike() -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path
    from scripts.mkm_inter_agent_ko_health_sidecar_v1 import sidecar_atom_sequence_for_text

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    lines = ALPHA_LINES_HEALTH + BETA_LINES_HEALTH
    backends = available_backends()
    by_backend: dict[str, Any] = {}

    for backend in backends:
        per_line: list[dict[str, Any]] = []
        for text in lines:
            toks, meta = morph_tokenize(text, prefer=backend)  # type: ignore[arg-type]
            lr = _lexicon_hit_rate(toks, path)
            sidecar_seq, sidecar_meta = sidecar_atom_sequence_for_text(text)
            per_line.append(
                {
                    "morph_meta": meta,
                    "lexicon": lr,
                    "sidecar_atom_id_count": len(sidecar_seq),
                    "sidecar_meta_status": sidecar_meta.get("status"),
                }
            )
        total_t = sum(r["lexicon"]["token_count"] for r in per_line)
        total_h = sum(r["lexicon"]["hit_count"] for r in per_line)
        by_backend[backend] = {
            "lines": per_line,
            "aggregate_hit_rate": round(total_h / total_t, 6) if total_t else None,
            "aggregate_token_count": total_t,
        }

    primary = backends[0]
    primary_block = by_backend.get(primary) or {}
    primary_rate = primary_block.get("aggregate_hit_rate")
    sidecar_atoms = sum(
        int((ln.get("sidecar_atom_id_count") or 0)) for ln in (primary_block.get("lines") or [])
    )
    ok = bool(backends) and primary_rate is not None and sidecar_atoms > 0

    return {
        "ok": ok,
        "schema": "mkm_inter_agent_ko_morphology_spike_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "corpus_line_count": len(lines),
        "backends_available": backends,
        "primary_backend": primary,
        "by_backend": by_backend,
        "sidecar_atom_total_primary_backend": sidecar_atoms,
        "note": "Morphology does not fix 0 hangul forms in main 41k; sidecar remains [HYPO] uplift path.",
        "boundary_ack": "M21 spike only; not production tokenizer or codebook merge.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_spike()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
