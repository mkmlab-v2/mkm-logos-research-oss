#!/usr/bin/env python3
"""Build Logos Studio evidence feedback summary from JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_ts_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _safe_div(a: float, b: float) -> float:
    if b <= 0:
        return 0.0
    return a / b


def _init_bucket() -> dict[str, Any]:
    return {
        "up": 0,
        "down": 0,
        "unknown": 0,
        "anchors": {},
        "issue_types": {"translation": 0, "context": 0, "source": 0, "other": 0, "unknown": 0},
    }


def _finalize_bucket(bucket: dict[str, Any], max_anchors: int = 10) -> dict[str, Any]:
    up = int(bucket["up"])
    down = int(bucket["down"])
    unknown = int(bucket["unknown"])
    total = up + down + unknown
    anchors = bucket["anchors"]
    top_anchors = sorted(anchors.items(), key=lambda kv: kv[1]["total"], reverse=True)[:max_anchors]
    return {
        "counts": {"up": up, "down": down, "unknown": unknown, "total": total},
        "ratios": {
            "up_rate": round(_safe_div(up, total), 4),
            "down_rate": round(_safe_div(down, total), 4),
            "agreement_rate": round(_safe_div(up, up + down), 4),
        },
        "top_anchors": [{"evidence_anchor": anchor, **metrics} for anchor, metrics in top_anchors],
        "top_issue_types": bucket["issue_types"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feedback-jsonl",
        default="memory/commercialization/logos_studio_evidence_feedback_v1.jsonl",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_studio_feedback_summary_latest.json",
    )
    parser.add_argument("--window-days", type=int, default=30)
    args = parser.parse_args()

    root = _root()
    src = root / args.feedback_jsonl
    out = root / args.out_json
    now = datetime.now(timezone.utc)
    lower = now - timedelta(days=max(1, args.window_days))
    lower_30 = now - timedelta(days=30)
    lower_7 = now - timedelta(days=7)

    line_count = 0
    parse_error_count = 0
    skipped_out_of_window = 0
    all_bucket = _init_bucket()
    w30_bucket = _init_bucket()
    w7_bucket = _init_bucket()

    if src.is_file():
        with src.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    parse_error_count += 1
                    continue
                if not isinstance(row, dict):
                    parse_error_count += 1
                    continue
                ts = _parse_ts_utc(row.get("ts_utc"))
                if ts is not None and ts < lower:
                    skipped_out_of_window += 1
                    continue
                verdict = str(row.get("verdict") or "").lower()
                issue_type = str(row.get("issue_type") or "").lower()
                if issue_type not in ("translation", "context", "source", "other"):
                    issue_type = "unknown"
                anchor = str(row.get("evidence_anchor") or "").strip()[:240] or "unknown"

                def apply(bucket: dict[str, Any]) -> None:
                    if verdict == "up":
                        bucket["up"] += 1
                    elif verdict == "down":
                        bucket["down"] += 1
                    else:
                        bucket["unknown"] += 1
                    bucket["issue_types"][issue_type] += 1
                    node = bucket["anchors"].setdefault(
                        anchor, {"up": 0, "down": 0, "unknown": 0, "total": 0}
                    )
                    node["total"] += 1
                    node[
                        "up" if verdict == "up" else "down" if verdict == "down" else "unknown"
                    ] += 1

                apply(all_bucket)
                if ts is not None and ts >= lower_30:
                    apply(w30_bucket)
                if ts is not None and ts >= lower_7:
                    apply(w7_bucket)

    all_stats = _finalize_bucket(all_bucket)
    w30 = _finalize_bucket(w30_bucket)
    w7 = _finalize_bucket(w7_bucket)
    report = {
        "schema": "logos_studio_feedback_summary_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": max(1, args.window_days),
        "source": {
            "feedback_jsonl": _display_path(src, root),
            "source_exists": src.is_file(),
            "line_count": line_count,
            "parse_error_count": parse_error_count,
            "skipped_out_of_window": skipped_out_of_window,
        },
        "counts": all_stats["counts"],
        "ratios": all_stats["ratios"],
        "top_anchors": all_stats["top_anchors"],
        "top_issue_types": all_stats["top_issue_types"],
        "windows": {"w7": w7, "w30": w30},
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "schema": report["schema"], "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

