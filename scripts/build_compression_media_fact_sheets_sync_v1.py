#!/usr/bin/env python3
"""Sync media fact sheet MD metrics from compression_public_reproduce_pack (SKU-separated)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPRODUCE = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
HANDOFF_MD = ROOT / "docs/final/artifacts/media_fact_sheet_handoff_governance_v1_latest.md"
API_MD = ROOT / "docs/final/artifacts/media_fact_sheet_compression_api_v1_latest.md"
INDEX_JSON = ROOT / "docs/final/artifacts/media_fact_sheet_index_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _replace_table_cell(md: str, row_label: str, new_value: str) -> str:
    pattern = rf"(\| {re.escape(row_label)} \|)[^|]*(\|)"
    repl = rf"\1 **{new_value}** \2"
    return re.sub(pattern, repl, md, count=1)


def _fmt_token_cell(value: Any, *, suffix: str = " tokens") -> str:
    if value is None or value == "—":
        return f"—{suffix}".replace(" tokens tokens", " tokens")
    if isinstance(value, (int, float)):
        return f"{int(value):,}{suffix}"
    return f"{value}{suffix}"


def sync_handoff(md: str, pack: dict[str, Any]) -> str:
    sku = (pack.get("skus") or {}).get("handoff_governance") or {}
    md = re.sub(
        r"generated_at_utc: [^\n]+",
        f"generated_at_utc: {_utc()}",
        md,
        count=1,
    )
    md = _replace_table_cell(md, "Inject OFF", _fmt_token_cell(sku.get("inject_off_tokens")))
    md = _replace_table_cell(
        md,
        "Full anchor paste",
        _fmt_token_cell(sku.get("full_anchor_tokens_top_n")),
    )
    pct = sku.get("reduction_percent_vs_full")
    pct_display = "—" if pct is None else f"~{pct}%"
    md = _replace_table_cell(md, "Reduction vs full", pct_display)
    return md


def sync_api(md: str, pack: dict[str, Any]) -> str:
    skus = pack.get("skus") or {}
    open_long = (skus.get("compression_api_open_structured_long") or {}).get("metrics") or {}
    track_a = skus.get("compression_api_track_a_reference") or {}
    md = re.sub(
        r"generated_at_utc: [^\n]+",
        f"generated_at_utc: {_utc()}",
        md,
        count=1,
    )
    saving = open_long.get("mean_token_saving_rate_proxy")
    jacc = open_long.get("mean_jaccard_proxy")
    case_n = open_long.get("case_count") or "?"
    if saving is not None:
        md = _replace_table_cell(
            md,
            "Open long structured",
            f"saving **{100 * float(saving):.1f}%** · J **{float(jacc):.4f}** ({case_n}-case corpus)",
        )
    pilot = (skus.get("pilot_roi") or {}).get("measured_proxy") or {}
    if pilot.get("mean_token_saving_rate_proxy") is not None:
        ps = float(pilot["mean_token_saving_rate_proxy"])
        pj = float(pilot.get("mean_jaccard_proxy") or 0)
        pc = pilot.get("case_count") or "?"
        md = _replace_table_cell(
            md,
            "Prospect pilot rehearsal",
            f"saving **{100 * ps:.1f}%** · J **{pj:.4f}** ({pc}-case)",
        )
    g40 = (skus.get("compression_api_golden40_public_safe") or {}).get("metrics") or {}
    g_s = g40.get("mean_token_saving_rate_proxy")
    g_j = g40.get("mean_jaccard_proxy")
    if g_s is not None:
        md = _replace_table_cell(
            md,
            "Golden40 public-safe",
            f"saving **{100 * float(g_s):.1f}%** · J **{float(g_j):.4f}** (40-case public-safe)",
        )
    md = _replace_table_cell(
        md,
        "Track A frozen",
        f"saving **~{100 * float(track_a.get('global_token_saving_rate', 0)):.1f}%** · Jaccard **~{float(track_a.get('avg_jaccard', 0)):.2f}**",
    )
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-json", type=Path, default=REPRODUCE)
    args = ap.parse_args()
    if not args.pack_json.is_file():
        print(json.dumps({"ok": False, "error": "missing reproduce pack"}))
        return 1
    pack = _load(args.pack_json)
    HANDOFF_MD.write_text(sync_handoff(HANDOFF_MD.read_text(encoding="utf-8"), pack), encoding="utf-8")
    API_MD.write_text(sync_api(API_MD.read_text(encoding="utf-8"), pack), encoding="utf-8")
    if INDEX_JSON.is_file():
        idx = _load(INDEX_JSON)
        idx["generated_at_utc"] = _utc()
        idx["synced_from"] = args.pack_json.relative_to(ROOT).as_posix()
        INDEX_JSON.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "handoff": str(HANDOFF_MD), "api": str(API_MD)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
