#!/usr/bin/env python3
"""Compare A-anchor (28,741 v2 core) vs U-anchor (31,102 single) Phase4 OS metrics side-by-side."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_verse_4d_anchor_ab_compare_v1_latest.json"
DEFAULT_A_CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_a_anchor_v1_latest.jsonl"
DEFAULT_U_CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
DEFAULT_OS_A = ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_a_anchor_v1_latest.json"
DEFAULT_OS_U = ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_u_anchor_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _pick_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    corpora = doc.get("corpora")
    canon: dict[str, Any] = {}
    if isinstance(corpora, list):
        for row in corpora:
            if isinstance(row, dict) and row.get("label") == "canon":
                canon = row
                break
    graph = canon.get("graph") if isinstance(canon.get("graph"), dict) else {}
    deltas = doc.get("deltas_vs_canon") if isinstance(doc.get("deltas_vs_canon"), dict) else {}
    nvp = deltas.get("null_vector_permutation") if isinstance(deltas.get("null_vector_permutation"), dict) else {}
    build = doc.get("build") if isinstance(doc.get("build"), dict) else {}
    return {
        "canon_rows": canon.get("rows"),
        "canon_mean_top1_cosine": canon.get("mean_top1_cosine"),
        "canon_top_medoid_centrality": graph.get("top_medoid_centrality"),
        "canon_gini_centrality": graph.get("gini_centrality"),
        "canon_edges_emitted": graph.get("edges_emitted"),
        "full_graph": build.get("full_graph"),
        "null_vector_perm_delta_top1": nvp.get("delta_mean_top1_cosine"),
        "null_vector_perm_delta_medoid": nvp.get("delta_top_medoid_centrality"),
        "null_vector_perm_delta_gini": nvp.get("delta_gini_centrality"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a-corpus", type=Path, default=DEFAULT_A_CORPUS)
    ap.add_argument("--u-corpus", type=Path, default=DEFAULT_U_CORPUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-phase4", action="store_true", help="Only diff existing os_compare files")
    args = ap.parse_args()

    py = sys.executable
    phase4 = ROOT / "scripts/run_logos_verse_4d_phase4_chain_v1.py"

    if not args.skip_phase4 and phase4.is_file():
        for label, corpus, os_out in (
            ("A", args.a_corpus, DEFAULT_OS_A),
            ("U", args.u_corpus, DEFAULT_OS_U),
        ):
            if not corpus.is_file():
                print(f"missing corpus {label}: {corpus}", file=sys.stderr)
                return 2
            cmd = [
                py,
                str(phase4),
                "--input-jsonl",
                str(corpus),
                "--full-graph",
                "--max-rows",
                "0",
            ]
            print(f"[anchor-ab] phase4 {label}", flush=True)
            rc = subprocess.call(cmd, cwd=str(ROOT))
            if rc != 0:
                return rc
            cmp_cmd = [
                py,
                str(ROOT / "scripts/compare_logos_verse_4d_os_metrics_v1.py"),
                "--corpus",
                f"canon={corpus}",
                "--out-json",
                str(os_out),
                "--full-graph",
                "--max-rows",
                "0",
            ]
            rc = subprocess.call(cmp_cmd, cwd=str(ROOT))
            if rc != 0:
                return rc

    os_a = _read_json(DEFAULT_OS_A)
    os_u = _read_json(DEFAULT_OS_U)
    if not os_a and not args.skip_phase4:
        os_a = _read_json(ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json")
    metrics_a = _pick_metrics(os_a)
    metrics_u = _pick_metrics(os_u)

    pack: dict[str, Any] = {
        "schema": "logos_verse_4d_anchor_ab_compare_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "anchor_A": {"label": "v2_core_28741", "corpus": str(args.a_corpus), "os_compare": metrics_a},
        "anchor_U": {"label": "single_anchor_31102", "corpus": str(args.u_corpus), "os_compare": metrics_u},
        "verdict_note": (
            "Research comparison only. U includes pipeline stubs where upstream lacks original text; "
            "not proof that U dominates A on lexical quality."
        ),
        "forbidden_claims": [
            "proven_cosmic_os",
            "perfect_canon_100_percent_lexical",
            "track_a_compression_auto_upgrade",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
