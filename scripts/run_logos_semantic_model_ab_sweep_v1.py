#!/usr/bin/env python3
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
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SQLITE = ART / "logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_QUERY_SET = ART / "logos_semantic_query_set_v2.json"
DEFAULT_OUT = ART / "logos_semantic_model_ab_sweep_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Logos semantic query suite model A/B sweep.")
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument(
        "--models",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2,sentence-transformers/all-mpnet-base-v2",
        help="Comma-separated sentence-transformers model ids.",
    )
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--thresholds", type=str, default="0.05,0.07,0.10,0.12,0.15,0.20")
    ap.add_argument("--target-low-conf-rate-max", type=float, default=0.60)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sqlite = args.sqlite if args.sqlite.is_absolute() else ROOT / args.sqlite
    query_set = args.query_set_json if args.query_set_json.is_absolute() else ROOT / args.query_set_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    model_ids = [m.strip() for m in args.models.split(",") if m.strip()]
    if not sqlite.is_file():
        raise SystemExit(f"Missing sqlite index: {sqlite}")
    if not query_set.is_file():
        raise SystemExit(f"Missing query set json: {query_set}")
    if not model_ids:
        raise SystemExit("No models provided")

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="logos_model_ab_") as td:
        tdp = Path(td)
        for model in model_ids:
            suite_out = tdp / f"suite_{abs(hash(model))}.json"
            sweep_out = tdp / f"sweep_{abs(hash(model))}.json"

            rc_suite, so, se = _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_logos_semantic_query_smoke_suite_v1.py"),
                    "--sqlite",
                    str(sqlite),
                    "--query-set-json",
                    str(query_set),
                    "--sentence-transformer-model",
                    model,
                    "--top-k",
                    str(int(args.top_k)),
                    "--output-json",
                    str(suite_out),
                ]
            )
            if rc_suite != 0:
                rows.append(
                    {
                        "model_id": model,
                        "status": "error",
                        "stage": "suite",
                        "error": (se or so).strip()[:500],
                    }
                )
                continue

            rc_sweep, wo, we = _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_logos_semantic_drift_threshold_sweep_v1.py"),
                    "--suite-json",
                    str(suite_out),
                    "--thresholds",
                    args.thresholds,
                    "--target-low-conf-rate-max",
                    str(float(args.target_low_conf_rate_max)),
                    "--output-json",
                    str(sweep_out),
                ]
            )
            if rc_sweep != 0:
                rows.append(
                    {
                        "model_id": model,
                        "status": "error",
                        "stage": "threshold_sweep",
                        "error": (we or wo).strip()[:500],
                    }
                )
                continue

            suite_doc = _read_json(suite_out)
            sweep_doc = _read_json(sweep_out)
            summary = suite_doc.get("summary") if isinstance(suite_doc.get("summary"), dict) else {}
            rec = sweep_doc.get("recommended_row") if isinstance(sweep_doc.get("recommended_row"), dict) else {}
            rows.append(
                {
                    "model_id": model,
                    "status": "ok",
                    "queries_ok": summary.get("queries_ok"),
                    "queries_error": summary.get("queries_error"),
                    "mean_top1_cosine": summary.get("mean_top1_cosine"),
                    "recommended_min_cosine": sweep_doc.get("recommended_min_cosine"),
                    "recommended_low_confidence_rate": rec.get("low_confidence_rate"),
                    "decision": sweep_doc.get("decision"),
                }
            )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    best = None
    if ok_rows:
        best = sorted(
            ok_rows,
            key=lambda r: (
                float(r.get("mean_top1_cosine") or 0.0),
                -float(r.get("recommended_low_confidence_rate") or 1.0),
            ),
            reverse=True,
        )[0]

    result = {
        "schema": "logos_semantic_model_ab_sweep_v1",
        "generated_at_utc": _now(),
        "sqlite_path": str(sqlite.resolve()),
        "query_set_path": str(query_set.resolve()),
        "models": model_ids,
        "rows": rows,
        "best_model_candidate": best,
        "decision": "FOUND_CANDIDATE" if best else "NO_VALID_MODEL_RESULT",
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "decision": result["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

