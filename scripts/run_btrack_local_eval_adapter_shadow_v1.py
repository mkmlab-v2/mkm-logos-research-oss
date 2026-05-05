#!/usr/bin/env python3
"""Run local shadow eval adapter sample for B-track."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_text(text: str) -> float:
    # Deterministic toy heuristic for shadow-only comparison.
    n = len(text.strip())
    if n <= 0:
        return 0.0
    return max(0.0, min(1.0, n / 2000.0))


def _decision(score: float) -> str:
    if score >= 0.7:
        return "PASS"
    if score >= 0.4:
        return "WATCH"
    return "REVIEW"


def _discover_default_inputs(root: Path, limit: int = 24) -> list[Path]:
    patterns = [
        "docs/final/LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md",
        "docs/external_research/AI-Logos_Research_Bibliography_2026.md",
        "docs/final/artifacts/btrack_*.json",
        "docs/final/artifacts/chronicle_*_latest.json",
        "docs/final/artifacts/chronicle_*_latest.jsonl",
        "docs/final/artifacts/global_atom_*_latest.json",
        "docs/final/artifacts/*_dashboard*_latest.md",
    ]
    seen: set[str] = set()
    out: list[Path] = []
    for pat in patterns:
        for p in sorted(root.glob(pat)):
            if not p.is_file():
                continue
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
            if len(out) >= limit:
                return out
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_contract = root / "docs" / "final" / "artifacts" / "btrack_local_eval_adapter_contract_v1.json"
    default_out = root / "docs" / "final" / "artifacts" / "btrack_local_eval_adapter_shadow_latest.json"
    default_inputs = _discover_default_inputs(root, limit=24)

    ap = argparse.ArgumentParser(description="Run local eval adapter shadow sample.")
    ap.add_argument("--contract-json", default=str(default_contract))
    ap.add_argument("--output-json", default=str(default_out))
    ap.add_argument("--input-file", action="append", default=[])
    args = ap.parse_args()
    input_files = args.input_file if args.input_file else [str(p) for p in default_inputs]

    contract = json.loads(Path(args.contract_json).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for idx, p in enumerate(input_files, start=1):
        path = Path(p)
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        score = round(_score_text(text), 6)
        rows.append(
            {
                "sample_id": f"shadow_sample_{idx:02d}",
                "source_ref": str(path).replace("\\", "/"),
                "score": score,
                "decision": _decision(score),
                "notes": "B-track shadow heuristic only"
            }
        )

    out = {
        "schema": "btrack_local_eval_adapter_shadow_v1",
        "generated_at_utc": _iso_now(),
        "contract_ref": str(Path(args.contract_json)).replace("\\", "/"),
        "track": "B",
        "mode": "shadow_only",
        "auto_bind_to_atrack_forbidden": True,
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "avg_score": round(sum(r["score"] for r in rows) / max(1, len(rows)), 6),
            "decisions": {
                "PASS": sum(1 for r in rows if r["decision"] == "PASS"),
                "WATCH": sum(1 for r in rows if r["decision"] == "WATCH"),
                "REVIEW": sum(1 for r in rows if r["decision"] == "REVIEW"),
            }
        },
        "governance": contract.get("governance", {})
    }
    Path(args.output_json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(Path(args.output_json)), "row_count": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
