#!/usr/bin/env python3
"""Query a themed logos vector index built by build_logos_themed_vector_index_v1.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ART = ROOT / "docs/final/artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--query", default="", help="Override preset graphrag_query_ko")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--output-json", type=Path, default=None)
    args = ap.parse_args()

    sidecar_path = ART / f"logos_themed_vector_{args.theme}_sidecar_latest.json"
    if not sidecar_path.is_file():
        print(f"Missing sidecar (build first): {sidecar_path}", file=sys.stderr)
        return 2

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8-sig"))
    sqlite = ROOT / str(sidecar.get("sqlite") or "")
    if not sqlite.is_file():
        print(f"Missing sqlite: {sqlite}", file=sys.stderr)
        return 2

    query = args.query.strip() or str(sidecar.get("graphrag_query_ko") or args.theme)
    out_path = args.output_json or (ART / f"logos_themed_vector_query_{args.theme}_latest.json")

    build_report = ART / f"logos_themed_vector_{args.theme}_v1_latest.json"
    st_model: str | None = None
    if build_report.is_file():
        try:
            br = json.loads(build_report.read_text(encoding="utf-8-sig"))
            if br.get("embedding_mode") == "sentence_transformers_v1":
                st_model = br.get("sentence_transformer_model_id") or br.get(
                    "sentence_transformer_model"
                )
        except json.JSONDecodeError:
            pass

    cmd = [
        PY,
        "scripts/query_logos_vector_index_ann_lite_v1.py",
        "--sqlite",
        str(sqlite),
        "--query",
        query,
        "--top-k",
        str(max(1, args.top_k)),
        "--output-json",
        str(out_path),
    ]
    if isinstance(st_model, str) and st_model.strip():
        cmd += ["--sentence-transformer-model", st_model.strip()]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    wrapper = {
        "schema": "logos_themed_vector_query_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "theme_id": args.theme,
        "query_ko": query,
        "query_result_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "sidecar": str(sidecar_path.relative_to(ROOT)).replace("\\", "/"),
    }
    wrapper_path = ART / f"logos_themed_vector_query_{args.theme}_wrapper_latest.json"
    wrapper_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "theme": args.theme,
                "out": str(out_path.relative_to(ROOT)),
                "wrapper": str(wrapper_path.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
