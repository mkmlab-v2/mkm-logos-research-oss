#!/usr/bin/env python3
"""B-track PoC: deterministic VA→Logos stub candidate fusion weights (white-box report).

Reads latest VA trajectory row and re-ranks stub ``verse_id`` candidates by tag-based
multipliers. Not a live embedding RAG index; regression-friendly trace only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VA = ROOT / "reports" / "va_trajectory_log_latest.json"
DEFAULT_STUB = ROOT / "tests" / "fixtures" / "cross_lens_fusion_candidates_sample_v1.json"
DEFAULT_OUT = ROOT / "reports" / "cross_lens_fusion_report_latest.json"

POLICY_ID = "va_tag_boost_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def fusion_multiplier(v: float, a: float, tags: list[str]) -> tuple[float, list[str]]:
    """Return (multiplier, matched rule tags) — documented in CONSTITUTION §3.8.1."""
    tl = [t.lower() for t in tags]
    matched: list[str] = []
    m = 1.0
    if v < -0.15:
        for key in ("peace", "comfort", "hope"):
            if key in tl:
                m *= 1.18
                matched.append(key)
                break
    if v > 0.25:
        for key in ("joy", "energy"):
            if key in tl:
                m *= 1.08
                matched.append(key)
                break
    if a > 0.45:
        for key in ("caution", "temperance"):
            if key in tl:
                m *= 1.12
                matched.append(key)
                break
    if a > 0.55:
        for key in ("calm", "peace"):
            if key in tl:
                m *= 1.15
                matched.append(key)
                break
    seen: list[str] = []
    for x in matched:
        if x not in seen:
            seen.append(x)
    return round(m, 6), seen


def build_report(
    va_doc: dict[str, Any],
    stub_path: Path,
    *,
    policy_notes: str | None = None,
) -> dict[str, Any]:
    stub = _read_json(stub_path)
    cands = stub.get("candidates")
    if not isinstance(cands, list) or not cands:
        raise ValueError("stub candidates missing or empty")

    traj = va_doc.get("trajectory") or {}
    cur = dict(traj.get("current_va") or {})
    v = float(cur.get("valence", 0.0))
    a = float(cur.get("arousal", 0.0))

    enriched: list[dict[str, Any]] = []
    for row in cands:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "")
        base = float(row.get("base_score") or 0.0)
        ftags = row.get("fusion_tags")
        tags = [str(x) for x in ftags] if isinstance(ftags, list) else []
        mult, matched = fusion_multiplier(v, a, tags)
        fw = round(base * mult, 6)
        enriched.append(
            {
                "verse_id": vid,
                "base_score": base,
                "fusion_tags": tags,
                "fusion_multiplier": mult,
                "fusion_weight": fw,
                "tags_matched": matched,
            }
        )

    by_base = sorted(enriched, key=lambda x: float(x["base_score"]), reverse=True)
    rank_before = {row["verse_id"]: i + 1 for i, row in enumerate(by_base)}

    by_fw = sorted(enriched, key=lambda x: float(x["fusion_weight"]), reverse=True)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(by_fw):
        vid = row["verse_id"]
        out_rows.append(
            {
                "verse_id": vid,
                "base_score": float(row["base_score"]),
                "fusion_multiplier": float(row["fusion_multiplier"]),
                "fusion_weight": float(row["fusion_weight"]),
                "rank_before": int(rank_before.get(vid, 99)),
                "rank_after": i + 1,
                "fusion_tags": list(row["fusion_tags"]),
                "tags_matched": list(row["tags_matched"]),
            }
        )

    notes = policy_notes or (
        "Low valence: first matching peace|comfort|hope ×1.18. "
        "High valence: joy|energy ×1.08. High arousal: caution|temperance ×1.12. "
        "Very high arousal: calm|peace cooldown ×1.15. Multipliers stack."
    )

    return {
        "schema": "cross_lens_fusion_report_v1",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "track_wall": ["NON_GATING", "ADVISORY_ONLY", "B_TRACK_RESEARCH"],
        "fusion_policy_id": POLICY_ID,
        "va_trajectory_source": "inline_or_cli",
        "va_snapshot": {
            "session_id": str(va_doc.get("session_id") or ""),
            "turn_index": int(va_doc.get("turn_index") or 0),
            "current_va": {"valence": v, "arousal": a},
        },
        "inputs": {
            "candidates_stub_path": str(stub_path.as_posix()),
        },
        "policy_notes": notes,
        "candidates_ranked": out_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--va-trajectory-json", type=Path, default=DEFAULT_VA)
    ap.add_argument("--candidates-stub-json", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--policy-notes", type=str, default=None)
    args = ap.parse_args()

    va_doc = _read_json(args.va_trajectory_json)
    if str(va_doc.get("schema")) != "va_trajectory_log_v1":
        print("ERR: --va-trajectory-json must be va_trajectory_log_v1", flush=True)
        return 2

    try:
        report = build_report(va_doc, args.candidates_stub_json, policy_notes=args.policy_notes)
    except ValueError as e:
        print(f"ERR: {e}", flush=True)
        return 2

    def _rel(p: Path) -> str:
        try:
            return p.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return p.as_posix()

    report["va_trajectory_source"] = _rel(args.va_trajectory_json)
    report["inputs"]["candidates_stub_path"] = _rel(args.candidates_stub_json)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    top = report["candidates_ranked"][0]["verse_id"] if report["candidates_ranked"] else ""
    print(json.dumps({"ok": True, "out": str(args.out), "top_verse_id": top}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
