#!/usr/bin/env python3
"""B-track v2 wire shadow A/B: economy OFF vs wire ON per bench case (JSONL, no active writes)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOLDEN = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BOOST = ROOT / "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_per_case_delta_v1.json"
DEFAULT_LOG = ROOT / "reports/constitution/btrack_pilot/v2_wire_shadow_metering_v1.jsonl"
ENV_KEY = "V2_WIRE_SHADOW_METERING_LOG_PATH"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_path(out: Path | None) -> Path:
    if out is not None:
        return out
    raw = os.environ.get(ENV_KEY, "").strip()
    return Path(raw) if raw else DEFAULT_LOG


def _load_cases(golden: Path, case_ids: list[str] | None, max_cases: int) -> list[dict[str, str]]:
    doc = json.loads(golden.read_text(encoding="utf-8"))
    rows = [c for c in doc.get("compression_cases") or [] if isinstance(c, dict)]
    if case_ids:
        want = set(case_ids)
        rows = [c for c in rows if str(c.get("id") or "") in want]
    if max_cases > 0:
        rows = rows[:max_cases]
    out: list[dict[str, str]] = []
    for c in rows:
        cid = str(c.get("id") or "").strip()
        raw = str(c.get("raw_text") or "").strip()
        if cid and raw:
            out.append({"id": cid, "raw_text": raw})
    return out


def _boost_case_ids() -> list[str]:
    if not BOOST.is_file():
        return []
    doc = json.loads(BOOST.read_text(encoding="utf-8"))
    return [str(r.get("case_id") or "") for r in doc.get("rows") or [] if r.get("case_id")]


def _meter_row(
    *,
    case_id: str,
    wire: bool,
    ev: dict[str, Any],
    elapsed_ms: float,
) -> dict[str, Any]:
    gr = ev.get("global_ratio")
    jac = ev.get("jaccard")
    sp = ev.get("semantic_pointer") if isinstance(ev.get("semantic_pointer"), dict) else {}
    gw = sp.get("graph_wire_influence_v1") if isinstance(sp, dict) else {}
    bridge_boost = bool((gw or {}).get("bridge_boost")) if wire else False
    return {
        "meter_schema": "v2_wire_shadow_metering_v1",
        "ts_utc": _utc(),
        "research_only": True,
        "sla_track": "B_v2_wire_shadow",
        "case_id": case_id,
        "graph_wire_selective_bridge": wire,
        "compression_profile": "economy",
        "tokens_before": int(ev.get("token_in") or 0),
        "tokens_after": int(ev.get("token_out") or 0),
        "global_token_saving_rate": float(gr) if gr is not None else None,
        "reconstruction_fidelity_jaccard": float(jac) if jac is not None else None,
        "graph_wire_bridge_boost": bridge_boost,
        "evaluate_ok": bool(ev.get("ok")),
        "elapsed_ms": elapsed_ms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-json", type=Path, default=GOLDEN)
    ap.add_argument("--out-jsonl", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=5, help="0 = all selected")
    ap.add_argument(
        "--case-ids",
        nargs="*",
        default=None,
        help="Subset of cmp2_* ids; default = bridge_boost rows from comp_atom05",
    )
    ap.add_argument("--append", action="store_true", help="Append to log (default: truncate then write)")
    args = ap.parse_args()

    from scripts.compression_token_api_v2_stub import _run_evaluate_for_packet  # noqa: WPS433

    case_ids = args.case_ids if args.case_ids else _boost_case_ids()
    cases = _load_cases(args.golden_json, case_ids or None, args.max_cases)
    if not cases:
        print(json.dumps({"ok": False, "error": "no_cases"}, ensure_ascii=False))
        return 1

    log_path = _log_path(args.out_jsonl)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    written = 0
    with log_path.open(mode, encoding="utf-8") as fh:
        for row in cases:
            cid = row["id"]
            text = row["raw_text"]
            for wire in (False, True):
                ev = _run_evaluate_for_packet(
                    text,
                    "semantic_general",
                    emit_semantic_pointer=wire,
                    graph_wire_selective_bridge=wire,
                    client_request_id=cid,
                    routing_profile="track_a_promoted",
                    compression_profile="economy",
                )
                line = _meter_row(
                    case_id=cid,
                    wire=wire,
                    ev=ev,
                    elapsed_ms=float(ev.get("elapsed_ms") or 0),
                )
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                written += 1

    try:
        log_rel = str(log_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        log_rel = str(log_path.resolve()).replace("\\", "/")
    meta = {
        "ok": True,
        "schema": "v2_wire_shadow_metering_bench_run_v1",
        "generated_at_utc": _utc(),
        "cases": len(cases),
        "lines_written": written,
        "log_path": log_rel,
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
