#!/usr/bin/env python3
"""M11: atom_id_sequence → lexicon gloss report (human review decoder, research_only)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_atom_gloss_decode_v1_latest.json"

SAMPLES = {
    "trading_en": "WATCH regime macro fragility BTC REDUCE exposure prophecy dual-leg",
    "health_ko": "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈",
    "lexicon_dense": "strong morph greek logos bible reference kai mercy alpha beta",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_report() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        gloss_rows_for_atom_ids,
        resolve_latest_codebook_path,
    )

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    client = TestClient(app)
    samples_out: dict[str, Any] = {}

    for label, text in SAMPLES.items():
        enc = client.post(
            "/v1/research/mkm_lexicon_wire/encode",
            json={"text": text, "zstd_min_raw_bytes": 0},
        )
        enc_body = enc.json() if enc.status_code == 200 else {}
        atom_ids = enc_body.get("atom_id_sequence") or []
        gloss, meta = gloss_rows_for_atom_ids(atom_ids, path)
        gloss_text = " ".join(r["gloss"] for r in gloss if r.get("gloss"))
        samples_out[label] = {
            "source_text": text,
            "atom_id_count": len(atom_ids),
            "gloss_text": gloss_text,
            "gloss_rows": gloss,
            "meta": meta,
        }

    return {
        "ok": True,
        "schema": "mkm_inter_agent_atom_gloss_decode_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "samples": samples_out,
        "boundary_ack": "Gloss = lexicon normalized_form lookup; not lossless decode or Track A claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
