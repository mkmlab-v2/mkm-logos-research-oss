#!/usr/bin/env python3
"""Update latest run index for symbol C validation pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_INDEX = REPORT_DIR / "symbol_c_validation_run_index_latest.json"
DEFAULT_PACKET = REPORT_DIR / "symbol_c_validation_packet_latest.json"
DEFAULT_BASELINE = REPORT_DIR / "symbol_c_validation_packet_baseline_latest.json"
DEFAULT_COMPARE = REPORT_DIR / "symbol_c_validation_queue_compare_latest.json"
DEFAULT_HISTORY_ROOT = REPORT_DIR / "history" / "symbol_c_validation"
DEFAULT_ALERT_TEMPLATE_STABLE = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_trend_alert_template_stable.json"
)
DEFAULT_ALERT_TEMPLATE_STRICT = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_trend_alert_template_strict.json"
)


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread_or_none(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_history_dir(history_root: Path) -> str | None:
    if not history_root.is_dir():
        return None
    dirs = [p for p in history_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.name).name


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _extract_history_packet_snapshot(history_dir: Path) -> dict[str, float | str | None]:
    packet_files = sorted(history_dir.glob("symbol_c_validation_packet_*.json"))
    if not packet_files:
        return {
            "run_id": history_dir.name,
            "stable_task_count": None,
            "exploratory_task_count": None,
            "top_overlap_rate": None,
        }
    packet = _jread_or_none(packet_files[-1]) or {}
    snap = packet.get("snapshot", {}) if isinstance(packet, dict) else {}
    return {
        "run_id": history_dir.name,
        "stable_task_count": _as_float(snap.get("stable_task_count")),
        "exploratory_task_count": _as_float(snap.get("exploratory_task_count")),
        "top_overlap_rate": _as_float(snap.get("top_overlap_rate")),
    }


def _build_trend(history_root: Path, trend_n: int) -> dict[str, Any]:
    if not history_root.is_dir():
        return {"window_size": trend_n, "points": [], "delta": {}}
    dirs = [p for p in history_root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name, reverse=True)
    selected = dirs[: max(1, trend_n)]
    points_desc = [_extract_history_packet_snapshot(d) for d in selected]
    points = list(reversed(points_desc))

    delta: dict[str, float | None] = {}
    if len(points) >= 2:
        first = points[0]
        last = points[-1]
        for k in ("stable_task_count", "exploratory_task_count", "top_overlap_rate"):
            fv = _as_float(first.get(k))
            lv = _as_float(last.get(k))
            delta[f"{k}_delta"] = None if fv is None or lv is None else (lv - fv)
    return {"window_size": trend_n, "points": points, "delta": delta}


def _load_alert_template(path: Path) -> dict[str, Any]:
    data = _jread_or_none(path)
    if not isinstance(data, dict):
        return {}
    return data


def _count_consecutive_negative_overlap(points: list[dict[str, Any]]) -> int:
    if len(points) < 2:
        return 0
    count = 0
    for i in range(len(points) - 1, 0, -1):
        curr = _as_float(points[i].get("top_overlap_rate"))
        prev = _as_float(points[i - 1].get("top_overlap_rate"))
        if curr is None or prev is None:
            break
        if (curr - prev) < 0:
            count += 1
            continue
        break
    return count


def _evaluate_trend_alerts(
    status: dict[str, Any],
    trend: dict[str, Any],
    alert_template: dict[str, Any],
) -> dict[str, Any]:
    min_latest_overlap_rate = float(alert_template.get("min_latest_overlap_rate", 0.5))
    min_latest_stable_tasks = int(alert_template.get("min_latest_stable_tasks", 20))
    min_latest_exploratory_tasks = int(alert_template.get("min_latest_exploratory_tasks", 20))
    negative_limit = int(alert_template.get("consecutive_negative_overlap_delta_limit", 3))

    failures: list[str] = []
    stable = _as_float(status.get("stable_task_count"))
    exploratory = _as_float(status.get("exploratory_task_count"))
    overlap = _as_float(status.get("top_overlap_rate"))
    if stable is None or stable < min_latest_stable_tasks:
        failures.append(f"latest stable_task_count below min ({stable} < {min_latest_stable_tasks})")
    if exploratory is None or exploratory < min_latest_exploratory_tasks:
        failures.append(f"latest exploratory_task_count below min ({exploratory} < {min_latest_exploratory_tasks})")
    if overlap is None or overlap < min_latest_overlap_rate:
        failures.append(f"latest top_overlap_rate below min ({overlap} < {min_latest_overlap_rate})")

    points = trend.get("points", [])
    negative_streak = _count_consecutive_negative_overlap(points) if isinstance(points, list) else 0
    if negative_streak >= negative_limit:
        failures.append(
            f"overlap negative delta streak exceeded limit (streak={negative_streak}, limit={negative_limit})"
        )

    return {
        "template": {
            "min_latest_overlap_rate": min_latest_overlap_rate,
            "min_latest_stable_tasks": min_latest_stable_tasks,
            "min_latest_exploratory_tasks": min_latest_exploratory_tasks,
            "consecutive_negative_overlap_delta_limit": negative_limit,
        },
        "observed": {
            "latest_stable_task_count": stable,
            "latest_exploratory_task_count": exploratory,
            "latest_top_overlap_rate": overlap,
            "consecutive_negative_overlap_delta": negative_streak,
        },
        "decision": "pass" if not failures else "hold",
        "failures": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Update latest symbol C validation run index")
    ap.add_argument("--index-out", default=str(DEFAULT_INDEX))
    ap.add_argument("--packet-json", default=str(DEFAULT_PACKET))
    ap.add_argument("--baseline-json", default=str(DEFAULT_BASELINE))
    ap.add_argument("--compare-json", default=str(DEFAULT_COMPARE))
    ap.add_argument("--history-root", default=str(DEFAULT_HISTORY_ROOT))
    ap.add_argument("--trend-n", type=int, default=5)
    ap.add_argument("--alert-template-stable", default=str(DEFAULT_ALERT_TEMPLATE_STABLE))
    ap.add_argument("--alert-template-strict", default=str(DEFAULT_ALERT_TEMPLATE_STRICT))
    args = ap.parse_args()

    index_out = _abs(args.index_out)
    packet = _jread_or_none(_abs(args.packet_json))
    baseline = _jread_or_none(_abs(args.baseline_json))
    compare = _jread_or_none(_abs(args.compare_json))
    history_root = _abs(args.history_root)
    latest_history = _latest_history_dir(history_root)
    trend = _build_trend(history_root, max(1, int(args.trend_n)))
    stable_template_path = _abs(args.alert_template_stable)
    strict_template_path = _abs(args.alert_template_strict)
    stable_alert_template = _load_alert_template(stable_template_path)
    strict_alert_template = _load_alert_template(strict_template_path)

    snapshot = packet.get("snapshot", {}) if isinstance(packet, dict) else {}
    baseline_snapshot = baseline.get("snapshot", {}) if isinstance(baseline, dict) else {}
    compare_summary = compare.get("summary", {}) if isinstance(compare, dict) else {}

    status = {
        "stable_task_count": snapshot.get("stable_task_count"),
        "exploratory_task_count": snapshot.get("exploratory_task_count"),
        "top_overlap_rate": snapshot.get("top_overlap_rate"),
        "baseline_stable_task_count": baseline_snapshot.get("stable_task_count"),
        "baseline_exploratory_task_count": baseline_snapshot.get("exploratory_task_count"),
        "baseline_top_overlap_rate": baseline_snapshot.get("top_overlap_rate"),
        "compare_top_overlap_count": compare_summary.get("top_overlap_count"),
        "compare_top_overlap_rate": compare_summary.get("top_overlap_rate"),
        "latest_history_dir": latest_history,
    }
    alert_profiles = {
        "stable": _evaluate_trend_alerts(status, trend, stable_alert_template),
        "strict": _evaluate_trend_alerts(status, trend, strict_alert_template),
    }

    payload = {
        "meta": {
            "kind": "symbol_c_validation_run_index",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "packet_json": str(_abs(args.packet_json)),
                "baseline_json": str(_abs(args.baseline_json)),
                "compare_json": str(_abs(args.compare_json)),
                "history_root": str(_abs(args.history_root)),
                "alert_template_stable": str(stable_template_path),
                "alert_template_strict": str(strict_template_path),
            },
        },
        "status": status,
        "trend": trend,
        "alert": alert_profiles.get("stable", {}),
        "alert_profiles": alert_profiles,
    }

    index_out.parent.mkdir(parents=True, exist_ok=True)
    index_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol C validation run index updated")
    print(f"out={index_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
