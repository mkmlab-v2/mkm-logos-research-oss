#!/usr/bin/env python3
"""FinOps L3 restore grid — holdout corpora only; wire codec + gloss proxy (B-track)."""

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

HOLDOUT = ROOT / "docs/final/artifacts/finops_wire_bench_holdout_v1_latest.json"
ENCODING_STATUS = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
DEFAULT_OUT = ROOT / "reports/finops_wire_l3_restore_grid_v1_latest.json"

from scripts.build_mkm_inter_agent_lexicon_hit_rate_bench_v1 import CORPORA  # noqa: E402

ZSTD_GRID = [0, 32, 64, 128]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _global_spike_reference() -> dict[str, Any]:
    st = _read(ENCODING_STATUS)
    m3 = (st.get("milestones") or {}).get("m3_human_decoder_public_copy") or {}
    rate = m3.get("avg_exact_restore_rate")
    return {
        "source": ENCODING_STATUS.relative_to(ROOT).as_posix(),
        "avg_exact_restore_rate": rate,
        "note": "Global L1 human-decoder spike; not re-run inside FinOps holdout grid.",
    }


def run_grid() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        gloss_rows_for_atom_ids,
        resolve_latest_codebook_path,
    )

    hold = _read(HOLDOUT)
    scenarios = list(hold.get("holdout_scenarios") or []) + list(hold.get("auxiliary_scenarios") or [])
    scenarios = [s for s in scenarios if s in CORPORA]
    if not scenarios:
        scenarios = [s for s in ("trading", "health", "lexicon_dense") if s in CORPORA]

    codebook = resolve_latest_codebook_path()
    if codebook is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    client = TestClient(app)
    cells: list[dict[str, Any]] = []

    for scenario in scenarios:
        lines = CORPORA.get(scenario) or []
        for zstd_min in ZSTD_GRID:
            use_ko = scenario == "health"
            line_rows: list[dict[str, Any]] = []
            wire_ok = 0
            gloss_known = 0
            gloss_total = 0

            for i, text in enumerate(lines, start=1):
                enc = client.post(
                    "/v1/research/mkm_lexicon_wire/encode",
                    json={
                        "text": text,
                        "zstd_min_raw_bytes": zstd_min,
                        "use_ko_health_sidecar": use_ko,
                    },
                )
                enc_body = enc.json() if enc.status_code == 200 else {}
                flags = enc_body.get("integrity_flags") or {}
                atom_ids = enc_body.get("atom_id_sequence") or []
                roundtrip = bool(flags.get("roundtrip_sanity")) and bool(atom_ids)

                dec = client.post(
                    "/v1/research/mkm_lexicon_wire/decode",
                    json={"wire_b64": enc_body.get("wire_b64") or ""},
                )
                dec_body = dec.json() if dec.status_code == 200 else {}
                decoded_atoms = dec_body.get("atom_id_sequence") or []
                atom_match = roundtrip and decoded_atoms == atom_ids

                gloss_rows, _ = gloss_rows_for_atom_ids(atom_ids, codebook)
                for row in gloss_rows:
                    gloss_total += 1
                    if row.get("known"):
                        gloss_known += 1
                gloss_text = " ".join(r.get("gloss") or "" for r in gloss_rows if r.get("gloss"))

                if atom_match:
                    wire_ok += 1

                line_rows.append(
                    {
                        "line_index": i,
                        "atom_wire_roundtrip_ok": atom_match,
                        "atom_id_count": len(atom_ids),
                        "wire_byte_len": enc_body.get("wire_byte_len"),
                        "codec_variant": enc_body.get("codec_variant"),
                        "gloss_preview": gloss_text[:120] if gloss_text else "",
                    }
                )

            n = len(lines) or 1
            cells.append(
                {
                    "scenario": scenario,
                    "zstd_min_raw_bytes": zstd_min,
                    "use_ko_health_sidecar": use_ko,
                    "line_count": len(lines),
                    "atom_wire_roundtrip_rate": round(wire_ok / n, 4),
                    "gloss_known_atom_ratio": round(gloss_known / gloss_total, 4) if gloss_total else None,
                    "lines": line_rows,
                }
            )

    trading_cells = [c for c in cells if c["scenario"] == "trading"]
    best_trading = max(trading_cells, key=lambda c: c["atom_wire_roundtrip_rate"]) if trading_cells else None

    return {
        "ok": True,
        "schema": "finops_wire_l3_restore_grid_v1",
        "generated_at_utc": _utc(),
        "domain_id": "finops_handoff_v1",
        "bench_seed": hold.get("bench_seed"),
        "holdout_contract": HOLDOUT.relative_to(ROOT).as_posix(),
        "scenarios_evaluated": scenarios,
        "grid_axes": {"zstd_min_raw_bytes": ZSTD_GRID},
        "cells": cells,
        "summary": {
            "trading_best_zstd_min": (best_trading or {}).get("zstd_min_raw_bytes"),
            "trading_best_atom_wire_roundtrip_rate": (best_trading or {}).get("atom_wire_roundtrip_rate"),
            "global_l1_text_restore_reference": _global_spike_reference(),
        },
        "forbidden_claims": hold.get("forbidden_claims") or [],
        "disclaimer_ko": (
            "본 그리드는 holdout 코퍼스·wire atom roundtrip·gloss 커버리지만 측정합니다. "
            "역복원 게이트(연구 스파이크) 기준 exact 복원률은 약 57.9%이며, "
            "무손실 통역·100% 복원·벤치 밖 일반화를 주장하지 않습니다."
        ),
        "research_only": True,
        "boundary_ack": "L3 bench-only grid; atom wire roundtrip != full text exact restore.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_grid()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json.resolve())}))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
