#!/usr/bin/env python3
"""Maintain shadow history for independent-lens fusion and emit gate decision."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FUSION_LATEST = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
HISTORY_JSONL = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_shadow_history.jsonl"
GATE_LATEST = ROOT / "docs" / "final" / "artifacts" / "independent_lens_shadow_gate_latest.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _month_tag(ts_value: Any) -> str:
    ts = str(ts_value or "").strip()
    return ts[:7] if len(ts) >= 7 else ""


def _append_history(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _looks_like_iso_utc(ts: str) -> bool:
    return len(ts) >= 20 and ts.endswith("Z") and "T" in ts


def _conflict_snapshot_from_fusion(fusion: dict[str, Any]) -> dict[str, Any]:
    """Compact audit fields from fusion conflict_summary + narrative digest (no full prose in JSONL)."""
    cs = fusion.get("conflict_summary") if isinstance(fusion.get("conflict_summary"), dict) else {}
    nar = cs.get("conflict_narrative_guarded")
    digest: str | None = None
    if isinstance(nar, str) and nar.strip():
        digest = hashlib.sha256(nar.strip().encode("utf-8")).hexdigest()
    return {
        "fusion_stub_version": fusion.get("version"),
        "minority_lens_ids": list(cs.get("minority_lens_ids") or []),
        "logos_evidence_verse_ids": list(cs.get("logos_evidence_verse_ids") or []),
        "conflict_narrative_sha256": digest,
        "majority_sign": cs.get("majority_sign"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Append independent lens fusion snapshot and build shadow gate.")
    ap.add_argument("--fusion-input", type=Path, default=FUSION_LATEST)
    ap.add_argument("--history-jsonl", type=Path, default=HISTORY_JSONL)
    ap.add_argument("--output", type=Path, default=GATE_LATEST)
    ap.add_argument("--min-weekly-cycles", type=int, default=8)
    ap.add_argument("--min-monthly-cycles", type=int, default=2)
    ap.add_argument(
        "--ts-override-utc",
        type=str,
        default="",
        help="Optional manual timestamp for a history row (ISO UTC, e.g. 2026-03-31T23:59:59Z).",
    )
    ap.add_argument(
        "--allow-ts-override",
        action="store_true",
        help="Required safety flag to use --ts-override-utc.",
    )
    ap.add_argument(
        "--override-label",
        type=str,
        default="",
        help="Optional label recorded when timestamp override is used.",
    )
    args = ap.parse_args()

    fusion = _read_json(args.fusion_input)
    if not fusion:
        raise SystemExit(f"fusion input missing/invalid: {args.fusion_input}")

    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    history_ts_utc = now_utc
    if args.ts_override_utc:
        if not args.allow_ts_override:
            raise SystemExit("ts override requested but --allow-ts-override was not provided")
        if not _looks_like_iso_utc(args.ts_override_utc):
            raise SystemExit("invalid --ts-override-utc format; expected ISO UTC like 2026-03-31T23:59:59Z")
        history_ts_utc = args.ts_override_utc

    month_tag = now_utc[:7]
    snap = _conflict_snapshot_from_fusion(fusion)
    history_row = {
        "ts_utc": history_ts_utc,
        "source_ts_utc": fusion.get("ts_utc"),
        "consensus_sign": consensus.get("consensus_sign"),
        "consensus_score": consensus.get("consensus_score"),
        "consensus_confidence": consensus.get("consensus_confidence"),
        "agreement_rate": consensus.get("agreement_rate"),
        "conflict_count": consensus.get("conflict_count"),
        "available_count": consensus.get("available_count"),
        "mode": fusion.get("mode"),
        **snap,
    }
    if args.override_label:
        history_row["override_label"] = args.override_label
    _append_history(args.history_jsonl, history_row)

    history = _read_jsonl(args.history_jsonl)
    weekly_cycles = len(history)
    observed_month_tags = sorted({_month_tag(x.get("ts_utc")) for x in history if _month_tag(x.get("ts_utc"))})
    monthly_cycles = len(observed_month_tags)

    blockers: list[str] = []
    if weekly_cycles < args.min_weekly_cycles:
        blockers.append(f"weekly_cycles_lt_{args.min_weekly_cycles}")
    if monthly_cycles < args.min_monthly_cycles:
        blockers.append(f"monthly_cycles_lt_{args.min_monthly_cycles}")
    if str(fusion.get("mode") or "") != "observation_only":
        blockers.append("fusion_mode_not_observation_only")

    payload = {
        "schema": "independent_lens_shadow_gate_v1",
        "ts_utc": now_utc,
        "month_tag": month_tag,
        "policy": {
            "a_track_binding": "forbidden",
            "recommended_mode": "observation_only",
            "min_weekly_cycles": args.min_weekly_cycles,
            "min_monthly_cycles": args.min_monthly_cycles,
        },
        "history": {
            "weekly_cycles_observed": weekly_cycles,
            "monthly_cycles_observed": monthly_cycles,
            "observed_month_tags": observed_month_tags,
            "history_path": str(args.history_jsonl.resolve()),
        },
        "latest_consensus": consensus,
        "latest_conflict_snapshot": snap,
        "decision": "KEEP_OBSERVATION_ONLY",
        "allow_a_track_binding": False,
        "blockers": blockers,
        "blocker_resolution_plan": {
            "monthly_cycles_lt_2": {
                "action": "accumulate at least one additional month-tagged observation cycle",
                "target": f">= {args.min_monthly_cycles} unique monthly tags in shadow history",
                "verification": "monthly_cycles_observed >= min_monthly_cycles",
            },
            "weekly_cycles_lt_min": {
                "action": "continue weekly observation until threshold is met",
                "target": f">= {args.min_weekly_cycles} cycles",
                "verification": "weekly_cycles_observed >= min_weekly_cycles",
            },
        },
        "manual_review_requirements": {
            "must_keep_observation_only": True,
            "required_checks_before_any_promotion_discussion": [
                "shadow blockers empty",
                "contract alignment unchanged",
                "data quality status PASS",
                "no Track B to Track A auto bridge",
            ],
        },
        "note": "Shadow gate only; this file must not be used as direct live trading trigger.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
