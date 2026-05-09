#!/usr/bin/env python3
"""Build one-file trading observation brief from latest artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GO = ROOT / "docs" / "final" / "artifacts" / "trading_go_no_go_latest.json"
DEFAULT_COVERAGE = ROOT / "docs" / "final" / "artifacts" / "protective_order_coverage_latest.json"
DEFAULT_PROMOTION = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "exports"
    / "cursor_trade_history"
    / "strategy_promotion_gate_latest.json"
)
DEFAULT_WINDOW = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "exports"
    / "cursor_trade_history"
    / "cursor_trade_history_latest_24h.json"
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "trading_observation_brief_latest.json"


def _read_obj(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--go-status", type=Path, default=DEFAULT_GO)
    ap.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--window", type=Path, default=DEFAULT_WINDOW)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    go_path = args.go_status if args.go_status.is_absolute() else (ROOT / args.go_status)
    coverage_path = args.coverage if args.coverage.is_absolute() else (ROOT / args.coverage)
    promotion_path = args.promotion_gate if args.promotion_gate.is_absolute() else (ROOT / args.promotion_gate)
    window_path = args.window if args.window.is_absolute() else (ROOT / args.window)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    go_doc = _read_obj(go_path) or {}
    coverage_doc = _read_obj(coverage_path) or {}
    promotion_doc = _read_obj(promotion_path) or {}
    window_doc = _read_obj(window_path) or {}

    go = str(go_doc.get("go_no_go") or "UNKNOWN")
    coverage = str(coverage_doc.get("status") or "unknown")
    promotion_ready = bool(((promotion_doc.get("decision") or {}).get("promotion_ready")) is True)
    counts = window_doc.get("counts") if isinstance(window_doc.get("counts"), dict) else {}
    treatment_count = int(counts.get("treatment", 0) or 0)
    total_count = int(counts.get("total", 0) or 0)

    summary_line = (
        f"GO_NO_GO={go} | coverage={coverage} | "
        f"promotion_ready={'true' if promotion_ready else 'false'} | "
        f"trades24h={treatment_count}/{total_count}"
    )

    out_doc: dict[str, Any] = {
        "schema": "trading_observation_brief_v1",
        "generated_at_utc": _utc_now(),
        "summary_line": summary_line,
        "go_no_go": go,
        "protective_coverage_status": coverage,
        "promotion_ready": promotion_ready,
        "counts_24h": {
            "treatment": treatment_count,
            "total": total_count,
        },
        "sources": {
            "go_status_path": str(go_path),
            "coverage_path": str(coverage_path),
            "promotion_gate_path": str(promotion_path),
            "window_path": str(window_path),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(summary_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
