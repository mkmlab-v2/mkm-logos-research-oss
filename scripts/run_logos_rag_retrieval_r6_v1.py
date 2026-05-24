#!/usr/bin/env python3
"""R6: v3 bilingual query set + ko_only pilot default + eval bundle (B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402
from scripts.logos_rag_bilingual_query_v1 import (  # noqa: E402
    DEFAULT_V3_BILINGUAL,
    KO_ONLY_RETRIEVAL_KNOBS,
    en_queries_from_items,
    ko_queries_from_items,
    load_bilingual_items,
)
from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_MEDOIDS,
    DEFAULT_SQLITE,
    _eval_profile,
    _load_index,
    _load_medoid_weights,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_r6_v1_latest.json"
BOOTSTRAP = ROOT / "scripts/bootstrap_logos_semantic_query_set_v3_bilingual_v1.py"
PILOT_SCRIPT = ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"
HYBRID_SWEEP = ROOT / "scripts/run_logos_rag_hybrid_improvement_sweep_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bilingual-json", type=Path, default=DEFAULT_V3_BILINGUAL)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--model-id", default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-bootstrap", action="store_true")
    ap.add_argument("--skip-pilot-probes", action="store_true")
    ap.add_argument("--skip-hybrid-sweep", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_bootstrap and not args.bilingual_json.is_file():
        steps.append(
            _run([sys.executable, str(BOOTSTRAP), "--output-json", str(args.bilingual_json)])
        )
        if steps[-1]["exit_code"] != 0:
            print(json.dumps({"ok": False, "steps": steps}, ensure_ascii=False), file=sys.stderr)
            return int(steps[-1]["exit_code"])

    if not args.bilingual_json.is_file():
        print(f"Missing bilingual set: {args.bilingual_json}", file=sys.stderr)
        return 2
    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2

    items = load_bilingual_items(args.bilingual_json)
    en_q = en_queries_from_items(items)
    ko_q = ko_queries_from_items(items, preprocessed=True)
    knobs = KO_ONLY_RETRIEVAL_KNOBS

    index_rows, dim, mode = _load_index(args.sqlite)
    medoid_weights = _load_medoid_weights(args.medoids_json)
    model = load_sentence_transformer(args.model_id)

    en_improved = _eval_profile(
        label="v3_en_improved",
        queries=en_q,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=True,
        improved=True,
        top_k=knobs["top_k"],
        max_k=knobs["max_k"],
        floor_abs=knobs["floor_abs"],
        floor_ratio=knobs["floor_ratio"],
        medoid_weights=medoid_weights,
        medoid_boost_cap=knobs["medoid_boost_cap"],
    )
    ko_primary = _eval_profile(
        label="v3_ko_gloss_ko_only_improved",
        queries=ko_q,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=True,
        top_k=knobs["top_k"],
        max_k=knobs["max_k"],
        floor_abs=knobs["floor_abs"],
        floor_ratio=knobs["floor_ratio"],
        medoid_weights=medoid_weights,
        medoid_boost_cap=knobs["medoid_boost_cap"],
    )

    pilot_rows: list[dict[str, Any]] = []
    if not args.skip_pilot_probes:
        for it in items[:3]:
            qid = str(it.get("id") or "")
            en = str(it.get("query_en") or "")
            out_path = PILOT / f"philosophy_lane_rag_pilot_r6_{qid}_ko_only_latest.json"
            step = _run(
                [
                    sys.executable,
                    str(PILOT_SCRIPT),
                    "--user-query",
                    en,
                    "--query-route",
                    "ko_only",
                    "--bilingual-map-json",
                    str(args.bilingual_json),
                    "--use-btrack-st-index",
                    "--out",
                    str(out_path),
                ],
                timeout=180,
            )
            top_score = None
            route_applied = None
            if out_path.is_file() and step["exit_code"] == 0:
                doc = json.loads(out_path.read_text(encoding="utf-8"))
                rag = doc.get("rag_query_route") if isinstance(doc.get("rag_query_route"), dict) else {}
                route_applied = rag.get("applied")
                ann = doc.get("ann_lite_query") if isinstance(doc.get("ann_lite_query"), dict) else {}
                tk = ann.get("top_k") if isinstance(ann.get("top_k"), list) else []
                if tk and isinstance(tk[0], dict):
                    top_score = tk[0].get("score")
            pilot_rows.append(
                {
                    "id": qid,
                    "query_en": en,
                    "exit_code": step["exit_code"],
                    "route_applied": route_applied,
                    "top_match_score": top_score,
                    "out_json": str(out_path),
                }
            )
            steps.append(step)

    hybrid_summary: dict[str, Any] | None = None
    if not args.skip_hybrid_sweep and HYBRID_SWEEP.is_file():
        hstep = _run([sys.executable, str(HYBRID_SWEEP)], timeout=600)
        steps.append(hstep)
        sweep_path = PILOT / "comp_logos_rag_hybrid_improvement_sweep_v1_latest.json"
        if sweep_path.is_file():
            hybrid_summary = json.loads(sweep_path.read_text(encoding="utf-8")).get("winner")

    en_mean = en_improved.get("mean_top1_cosine")
    ko_mean = ko_primary.get("mean_top1_cosine")
    delta = None
    if isinstance(en_mean, (int, float)) and isinstance(ko_mean, (int, float)):
        delta = round(float(ko_mean) - float(en_mean), 9)

    doc: dict[str, Any] = {
        "schema": "comp_logos_rag_retrieval_r6_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating_ack": True,
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
        "inputs": {
            "bilingual_json": str(args.bilingual_json.resolve()),
            "sqlite": str(args.sqlite.resolve()),
            "pilot_default_route": "ko_only",
            "items": len(items),
        },
        "knobs": knobs,
        "headline": {
            "v3_en_improved_mean_top1_cosine": en_mean,
            "v3_ko_gloss_ko_only_mean_top1_cosine": ko_mean,
            "delta_ko_minus_en": delta,
            "query_set_note": "v3_bilingual_v1 embeds query_ko; reports must split EN vs KO.",
        },
        "profiles": {
            "v3_en_improved": en_improved,
            "v3_ko_gloss_ko_only_improved": ko_primary,
        },
        "pilot_ko_only_probes": pilot_rows,
        "hybrid_sweep_winner": hybrid_summary,
        "steps": steps,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output_json),
                "en_mean": en_mean,
                "ko_mean": ko_mean,
                "delta": delta,
                "pilot_probes": len(pilot_rows),
            },
            ensure_ascii=False,
        )
    )
    failed = [s for s in steps if s.get("exit_code") not in (0, None)]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
