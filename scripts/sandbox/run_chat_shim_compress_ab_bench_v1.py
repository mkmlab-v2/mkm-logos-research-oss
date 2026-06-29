#!/usr/bin/env python3
"""[HYPO] Chat shim A/B bench — raw (override off) vs compress (shim on), B-track only."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl"
DEFAULT_OUT = ROOT / "reports/chat_shim_compress_ab_bench_v1_latest.json"
DEFAULT_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"

DEFAULT_SYSTEM = (
    "Task: coding agent bench. "
    "Constraints: B-track research_only, no active report mutation, pytest smoke. "
    "Files: scripts/*.py, data/btrack/*.jsonl, reports/*_latest.json. "
    "Verify with py -m pytest -q."
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text") is not None:
            rows.append(row)
    return rows


def _messages_for_case(case: dict[str, Any]) -> list[tuple[str, str]]:
    lane = str(case.get("lane") or "")
    raw = str(case["raw_text"])
    if lane == "agent_rules_excerpt":
        return [("system", raw), ("user", "Apply the rules above. Reply: ACK")]
    return [("system", DEFAULT_SYSTEM), ("user", raw)]


def _token_in(text: str) -> int:
    from scripts.run_cursor_coding_compress_bench_v1 import _token_in as tok

    return tok(text)


def _shim_off_tokens(pairs: list[tuple[str, str]]) -> int:
    return sum(_token_in(content) for _, content in pairs)


def _shim_on(pairs: list[tuple[str, str]]) -> tuple[int, list[dict[str, Any]], float]:
    from scripts.cursor_chat_shim_v1 import ChatMessage, _transform_messages

    t0 = time.perf_counter()
    msgs, audit = _transform_messages([ChatMessage(role=r, content=c) for r, c in pairs])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    total = 0
    for m, row in zip(msgs, audit):
        if row.get("skipped"):
            total += _token_in(str(m.get("content") or ""))
        else:
            total += int(row.get("token_out") or _token_in(str(m.get("content") or "")))
    return total, audit, elapsed_ms


def run_bench(
    *,
    input_path: Path,
    out_path: Path,
    hardening_path: Path,
    max_cases: int,
    min_raw_tokens: int,
    dry_run: bool,
) -> dict[str, Any]:
    import os

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()

    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "chat_shim_compress_ab_bench_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypothesis_tier": "B",
            "dry_run": True,
            "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "case_count": len(cases_in),
            "boundary_ack": "Dry-run only; no A/B rows.",
        }

    rows: list[dict[str, Any]] = []
    for case in cases_in:
        pairs = _messages_for_case(case)
        off = _shim_off_tokens(pairs)
        if off < min_raw_tokens:
            rows.append(
                {
                    "id": case.get("id"),
                    "lane": case.get("lane"),
                    "compressible": False,
                    "skip_reason": "below_min_raw_tokens",
                    "tokens_off": off,
                    "tokens_on": off,
                    "token_saving_rate": 0.0,
                    "compress_elapsed_ms": 0.0,
                }
            )
            continue

        on, audit, elapsed_ms = _shim_on(pairs)
        saving = 0.0 if off <= 0 else max(0.0, (off - on) / off)
        structured = any(isinstance(a, dict) and a.get("structured_preserve") for a in audit)

        rows.append(
            {
                "id": case.get("id"),
                "lane": case.get("lane"),
                "compressible": saving > 0.0 or any(not a.get("skipped") for a in audit),
                "tokens_off": off,
                "tokens_on": on,
                "token_saving_rate": round(saving, 6),
                "tokens_saved": off - on,
                "compress_elapsed_ms": round(elapsed_ms, 3),
                "structured_preserve": structured,
                "audit": audit,
            }
        )

    compressible = [r for r in rows if r.get("compressible") and r.get("token_saving_rate", 0) > 0]
    all_with_off = [r for r in rows if int(r.get("tokens_off") or 0) >= min_raw_tokens]

    def _avg(key: str, subset: list[dict[str, Any]]) -> float:
        if not subset:
            return 0.0
        return sum(float(r.get(key) or 0) for r in subset) / len(subset)

    aggregate = {
        "case_count": len(rows),
        "evaluated_count": len(all_with_off),
        "compressible_count": len(compressible),
        "avg_token_saving_rate_all_evaluated": round(_avg("token_saving_rate", all_with_off), 6),
        "avg_token_saving_rate_compressible_only": round(_avg("token_saving_rate", compressible), 6),
        "total_tokens_off": sum(int(r.get("tokens_off") or 0) for r in all_with_off),
        "total_tokens_on": sum(int(r.get("tokens_on") or 0) for r in all_with_off),
        "total_tokens_saved": sum(int(r.get("tokens_saved") or 0) for r in all_with_off),
        "avg_compress_elapsed_ms": round(_avg("compress_elapsed_ms", all_with_off), 3),
    }
    if aggregate["total_tokens_off"] > 0:
        aggregate["bundle_token_saving_rate"] = round(
            aggregate["total_tokens_saved"] / aggregate["total_tokens_off"], 6
        )
    else:
        aggregate["bundle_token_saving_rate"] = 0.0

    return {
        "schema": "chat_shim_compress_ab_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "min_raw_tokens": min_raw_tokens,
        "comparison": {
            "off_label": "shim_off_raw_messages",
            "on_label": "shim_on_compress_transform",
            "note": "Speed/latency of AI model not measured; compress_elapsed_ms is local shim only.",
        },
        "aggregate": aggregate,
        "cases": rows,
        "boundary_ack": "B-track bench; not Cursor IDE end-to-end billing proof.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--hardening", default=str(DEFAULT_HARDENING))
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--min-raw-tokens", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    hardening_path = Path(args.hardening)
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path

    if not args.dry_run and not input_path.is_file():
        raise SystemExit(f"missing input: {input_path}")

    doc = run_bench(
        input_path=input_path,
        out_path=out_path,
        hardening_path=hardening_path,
        max_cases=args.max_cases,
        min_raw_tokens=args.min_raw_tokens,
        dry_run=args.dry_run,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    if not args.dry_run:
        agg = doc.get("aggregate") or {}
        print(
            f"compressible={agg.get('compressible_count')}/{agg.get('evaluated_count')} "
            f"bundle_saving={agg.get('bundle_token_saving_rate')} "
            f"avg_compress_ms={agg.get('avg_compress_elapsed_ms')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
