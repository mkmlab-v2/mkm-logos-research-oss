#!/usr/bin/env python3
"""R4 smoke: philosophy pilot with auto KO route + ST index (3 probes)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = PILOT / "comp_logos_rag_pilot_r4_batch_latest.json"
PROBES = [
    ("en_probe", "covenant stability under crisis"),
    ("ko_probe", "위기 가운데 언약의 안정과 신실"),
    ("mixed_probe", "covenant 위기 속 언약 stability"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows: list[dict[str, Any]] = []
    for label, q in PROBES:
        out_path = PILOT / f"philosophy_lane_rag_pilot_r4_{label}_latest.json"
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "philosophy_lane_rag_pilot_v1.py"),
            "--user-query",
            q,
            "--top-k",
            "5",
            "--out",
            str(out_path),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        doc: dict[str, Any] = {}
        if out_path.is_file():
            doc = json.loads(out_path.read_text(encoding="utf-8"))
        top = {}
        ann = doc.get("ann_lite_query") if isinstance(doc.get("ann_lite_query"), dict) else {}
        tk = ann.get("top_k") if isinstance(ann.get("top_k"), list) else []
        if tk and isinstance(tk[0], dict):
            top = tk[0]
        rows.append(
            {
                "label": label,
                "user_query": q,
                "exit_code": proc.returncode,
                "status": doc.get("status"),
                "rag_query_route": doc.get("rag_query_route"),
                "top_match_verse_id": top.get("verse_id"),
                "top_match_score": top.get("score"),
                "out_json": str(out_path),
            }
        )
        if proc.returncode != 0:
            rows[-1]["stderr_tail"] = (proc.stderr or proc.stdout or "")[-400:]

    doc_out = {
        "schema": "comp_logos_rag_pilot_r4_batch_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "probes": rows,
        "track_wall": {"prophecy_promotion_gates_touch": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [r for r in rows if r.get("exit_code") != 0]
    print(json.dumps({"ok": not failed, "out": str(args.output_json), "failed": len(failed)}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
