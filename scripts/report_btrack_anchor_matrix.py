#!/usr/bin/env python3
"""Generate one-page anchor verification matrix (MD + JSON)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots_verified.jsonl"
CROSS_REF = ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
PAIR_BEFORE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_latest.jsonl"
PAIR_AFTER = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_anchor_verified_only_latest.jsonl"
OUT_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_anchor_matrix_latest.json"
OUT_MD = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_anchor_matrix_latest.md"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _state_id_from_key(key: Any) -> int | None:
    if not isinstance(key, str):
        return None
    if not key.startswith("STATE_"):
        return None
    try:
        return int(key.split("_", 1)[1])
    except ValueError:
        return None


def _flag_set(row: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    if bool(row.get("direction_match")):
        out.add("direction_match")
    try:
        if float(row.get("confidence_delta_b_minus_a", -1.0)) >= 0.0:
            out.add("confidence_non_negative")
    except (TypeError, ValueError):
        pass
    try:
        if float(row.get("snr_delta_b_minus_a", -1.0)) >= 0.0:
            out.add("snr_non_negative")
    except (TypeError, ValueError):
        pass
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def main() -> int:
    ap = argparse.ArgumentParser(description="Report B-Track anchor verification matrix")
    ap.add_argument("--slots", default=str(SLOTS))
    ap.add_argument("--cross-ref", default=str(CROSS_REF))
    ap.add_argument("--pair-before", default=str(PAIR_BEFORE))
    ap.add_argument("--pair-after", default=str(PAIR_AFTER))
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--out-md", default=str(OUT_MD))
    args = ap.parse_args()

    slots_path = _abs(args.slots)
    cross_ref_path = _abs(args.cross_ref)
    pair_before_path = _abs(args.pair_before)
    pair_after_path = _abs(args.pair_after)
    out_json = _abs(args.out_json)
    out_md = _abs(args.out_md)

    if not slots_path.is_file():
        print(f"ERROR: missing slots file: {slots_path}")
        return 2
    if not cross_ref_path.is_file():
        print(f"ERROR: missing cross ref file: {cross_ref_path}")
        return 2
    if not pair_before_path.is_file():
        print(f"ERROR: missing pair-before file: {pair_before_path}")
        return 2
    if not pair_after_path.is_file():
        print(f"ERROR: missing pair-after file: {pair_after_path}")
        return 2

    slots = _load_jsonl(slots_path)
    cross = json.loads(cross_ref_path.read_text(encoding="utf-8"))
    before_rows = _load_jsonl(pair_before_path)
    after_rows = _load_jsonl(pair_after_path)
    entries = [e for e in cross.get("entries", []) if isinstance(e, dict)]
    entry_by_state: dict[int, dict[str, Any]] = {}
    for e in entries:
        sid = e.get("state_candidate_id")
        if isinstance(sid, int) and sid not in entry_by_state:
            entry_by_state[sid] = e

    before_by_state: dict[int, dict[str, Any]] = {}
    after_by_state: dict[int, dict[str, Any]] = {}
    for r in before_rows:
        sid = _state_id_from_key(r.get("key"))
        if sid is not None:
            before_by_state[sid] = r
    for r in after_rows:
        sid = _state_id_from_key(r.get("key"))
        if sid is not None:
            after_by_state[sid] = r

    rows: list[dict[str, Any]] = []
    for s in slots:
        sid = s.get("state_id")
        if not isinstance(sid, int):
            continue
        e = entry_by_state.get(sid, {})
        before = before_by_state.get(sid, {})
        after = after_by_state.get(sid, {})
        before_flags = _flag_set(before)
        after_flags = _flag_set(after)
        before_conf_delta = float(before.get("confidence_delta_b_minus_a", 0.0)) if before else 0.0
        after_conf_delta = float(after.get("confidence_delta_b_minus_a", 0.0)) if after else 0.0
        before_snr_delta = float(before.get("snr_delta_b_minus_a", 0.0)) if before else 0.0
        after_snr_delta = float(after.get("snr_delta_b_minus_a", 0.0)) if after else 0.0
        conf_gain = after_conf_delta - before_conf_delta
        snr_gain = after_snr_delta - before_snr_delta
        rows.append(
            {
                "state_id": sid,
                "entry_id": e.get("entry_id"),
                "canonical_ref": e.get("canonical_ref"),
                "satellite_ref": e.get("satellite_ref"),
                "corpus_type": e.get("corpus_type"),
                "anchor_status": s.get("anchor_status"),
                "anchor_strength": s.get("anchor_strength"),
                "confidence_boost": s.get("confidence_boost"),
                "snr_boost": s.get("snr_boost"),
                "evidence_ref": s.get("evidence_ref"),
                "delta_before": {
                    "confidence_delta_b_minus_a": round(before_conf_delta, 6),
                    "snr_delta_b_minus_a": round(before_snr_delta, 6),
                },
                "delta_after": {
                    "confidence_delta_b_minus_a": round(after_conf_delta, 6),
                    "snr_delta_b_minus_a": round(after_snr_delta, 6),
                },
                "state_delta": {
                    "confidence_delta_gain": round(conf_gain, 6),
                    "snr_delta_gain": round(snr_gain, 6),
                    "jaccard_gate_flags_before_vs_after": round(_jaccard(before_flags, after_flags), 6),
                },
            }
        )
    rows.sort(key=lambda r: int(r["state_id"]))

    report = {
        "schema": "btrack_anchor_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "rows": len(rows),
            "verified_rows": sum(1 for r in rows if r.get("anchor_status") == "verified"),
        },
        "inputs": {
            "pair_before": str(pair_before_path),
            "pair_after": str(pair_after_path),
        },
        "impact_summary": {
            "avg_confidence_delta_gain": round(
                sum(float(r["state_delta"]["confidence_delta_gain"]) for r in rows) / len(rows), 6
            ) if rows else 0.0,
            "avg_snr_delta_gain": round(
                sum(float(r["state_delta"]["snr_delta_gain"]) for r in rows) / len(rows), 6
            ) if rows else 0.0,
            "avg_jaccard_gate_flags_before_vs_after": round(
                sum(float(r["state_delta"]["jaccard_gate_flags_before_vs_after"]) for r in rows) / len(rows), 6
            ) if rows else 0.0,
        },
        "rows": rows,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# B-Track Anchor Matrix (Verified)",
        "",
        f"- generated_at_utc: `{report['generated_at_utc']}`",
        f"- rows: **{report['counts']['rows']}**",
        f"- verified_rows: **{report['counts']['verified_rows']}**",
        "",
        f"- avg_confidence_delta_gain: **{report['impact_summary']['avg_confidence_delta_gain']:.6f}**",
        f"- avg_snr_delta_gain: **{report['impact_summary']['avg_snr_delta_gain']:.6f}**",
        f"- avg_jaccard_gate_flags_before_vs_after: **{report['impact_summary']['avg_jaccard_gate_flags_before_vs_after']:.6f}**",
        "",
        "| state_id | entry_id | canonical_ref | corpus_type | anchor_status | strength | conf_boost | snr_boost | conf_gain | snr_gain | jaccard |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['state_id']} | {r.get('entry_id') or '-'} | {r.get('canonical_ref') or '-'} | "
            f"{r.get('corpus_type') or '-'} | {r.get('anchor_status') or '-'} | "
            f"{r.get('anchor_strength') if r.get('anchor_strength') is not None else '-'} | "
            f"{r.get('confidence_boost') if r.get('confidence_boost') is not None else '-'} | "
            f"{r.get('snr_boost') if r.get('snr_boost') is not None else '-'} | "
            f"{r['state_delta']['confidence_delta_gain']:.6f} | {r['state_delta']['snr_delta_gain']:.6f} | "
            f"{r['state_delta']['jaccard_gate_flags_before_vs_after']:.6f} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("OK: anchor matrix reports generated")
    print(f"json={out_json}")
    print(f"md={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
