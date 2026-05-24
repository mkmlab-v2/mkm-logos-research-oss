#!/usr/bin/env python3
"""M18b: [HYPO] health sidecar overlay — atom coverage uplift vs baseline wire encode."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_wire_demo_v1_latest.json"

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import ALPHA_LINES_HEALTH, BETA_LINES_HEALTH  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_demo() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path
    from scripts.mkm_inter_agent_ko_health_sidecar_v1 import (
        DEFAULT_SIDECAR,
        merged_atom_sequence_for_text,
        sidecar_atom_sequence_for_text,
    )

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    client = TestClient(app)
    lines = ALPHA_LINES_HEALTH + BETA_LINES_HEALTH
    rows: list[dict[str, Any]] = []

    for i, text in enumerate(lines, start=1):
        enc = client.post(
            "/v1/research/mkm_lexicon_wire/encode",
            json={"text": text, "zstd_min_raw_bytes": 0},
        )
        enc_body = enc.json() if enc.status_code == 200 else {}
        baseline_atoms = len(enc_body.get("atom_id_sequence") or [])

        merged, merge_meta = merged_atom_sequence_for_text(
            text, path, DEFAULT_SIDECAR, tokenization="hangul_syllable"
        )
        side_only, _ = sidecar_atom_sequence_for_text(text, DEFAULT_SIDECAR, tokenization="hangul_syllable")

        rows.append(
            {
                "line_index": i,
                "char_len": len(text),
                "baseline_wire_atom_count": baseline_atoms,
                "sidecar_only_atom_count": len(side_only),
                "merged_atom_count": len(merged),
                "uplift_vs_baseline": len(merged) - baseline_atoms,
                "merge_meta": merge_meta,
            }
        )

    baseline_sum = sum(r["baseline_wire_atom_count"] for r in rows)
    merged_sum = sum(r["merged_atom_count"] for r in rows)
    return {
        "ok": True,
        "schema": "mkm_inter_agent_ko_health_sidecar_wire_demo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "sidecar_path": DEFAULT_SIDECAR.relative_to(ROOT).as_posix(),
        "line_count": len(rows),
        "lines": rows,
        "aggregate": {
            "baseline_wire_atom_count": baseline_sum,
            "merged_atom_count": merged_sum,
            "uplift_atoms": merged_sum - baseline_sum,
            "uplift_ratio": round(merged_sum / baseline_sum, 4) if baseline_sum else None,
        },
        "boundary_ack": (
            "[HYPO] Sidecar is not in production wire codec; demo shows coverage ceiling if overlay merged."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_demo()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
