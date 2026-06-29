#!/usr/bin/env python3
"""B-track: structural agent-extract gate on compressed coding context (no Cursor API)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface
from scripts.run_cursor_coding_compress_bench_v1 import (
    DEFAULT_HARDENING,
    DEFAULT_INPUT,
    _load_cases,
    _load_lane_intensity,
    _selected_profile,
    _token_in,
)

DEFAULT_EXPECT = ROOT / "data/btrack/cursor_coding_agent_extract_expect_v1.json"
DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_agent_extract_input_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/cursor_coding_agent_extract_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compressed_surface(text: str, profile: dict[str, Any], *, lane: str | None, lane_intensity: dict[str, str]) -> tuple[str, dict[str, Any]]:
    proxy = coding_proxy_compress_surface(text, profile, lane=lane, lane_intensity=lane_intensity)
    surface = str(proxy.get("surface") or "")
    proxy["compressed_len"] = len(surface)
    return surface, proxy


def _anchor_hits(surface: str, anchors: list[str]) -> list[dict[str, Any]]:
    low = surface.lower()
    rows: list[dict[str, Any]] = []
    for anchor in anchors:
        a = anchor.lower()
        rows.append({"anchor": anchor, "hit": a in low})
    return rows


def run_gate(
    input_path: Path,
    expect_path: Path,
    *,
    hardening_path: Path,
) -> dict[str, Any]:
    expect_doc = json.loads(expect_path.read_text(encoding="utf-8-sig"))
    cases_expect: dict[str, Any] = expect_doc.get("cases") or {}
    cases_in = {str(c.get("id")): c for c in _load_cases(input_path) if c.get("id")}

    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)

    evaluated: list[dict[str, Any]] = []
    for case_id, spec in cases_expect.items():
        if case_id not in cases_in:
            evaluated.append(
                {
                    "id": case_id,
                    "skipped": True,
                    "reason": "missing_input_case",
                    "pass": False,
                }
            )
            continue
        item = cases_in[case_id]
        raw = str(item["raw_text"])
        anchors = list(spec.get("anchors") or [])
        min_ratio = float(spec.get("min_hit_ratio", 1.0))
        surface_name = str(spec.get("surface") or "compressed_text_effective")

        surface, proxy = _compressed_surface(
            raw,
            profile,
            lane=str(item.get("lane")) if item.get("lane") else None,
            lane_intensity=lane_intensity,
        )
        hits = _anchor_hits(surface, anchors)
        hit_n = sum(1 for h in hits if h["hit"])
        ratio = (hit_n / len(anchors)) if anchors else 0.0
        case_pass = ratio >= min_ratio
        evaluated.append(
            {
                "id": case_id,
                "lane": item.get("lane"),
                "surface": surface_name,
                "proxy_path": proxy.get("proxy_path"),
                "token_in": _token_in(raw),
                "anchors_total": len(anchors),
                "anchors_hit": hit_n,
                "hit_ratio": ratio,
                "min_hit_ratio": min_ratio,
                "pass": case_pass,
                "hits": hits,
                "surface_preview": surface[:400],
            }
        )

    all_pass = all(r.get("pass") for r in evaluated if not r.get("skipped"))
    return {
        "schema": "cursor_coding_agent_extract_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "not_track_a_promotion",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "expect_path": str(expect_path.relative_to(ROOT)).replace("\\", "/"),
        "hardening_config": str(hardening_path.relative_to(ROOT)).replace("\\", "/"),
        "gate": {"pass": all_pass, "case_count": len(evaluated)},
        "cases": evaluated,
        "boundary_ack": "Structural anchor gate only; not a substitute for live Cursor Auto sessions.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent-extract structural gate for coding compress (B-track).")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--expect-json", default=str(DEFAULT_EXPECT))
    ap.add_argument("--hardening-config", default=str(DEFAULT_HARDENING))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    hardening_path = Path(args.hardening_config)
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path)
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()

    input_path = Path(args.input_jsonl)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    expect_path = Path(args.expect_json)
    if not expect_path.is_absolute():
        expect_path = ROOT / expect_path

    doc = run_gate(input_path, expect_path, hardening_path=hardening_path)
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0 if doc.get("gate", {}).get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
