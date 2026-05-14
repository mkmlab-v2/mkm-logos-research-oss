#!/usr/bin/env python3
"""Compare latest survivor panel vs optional JSONL history; write health alert JSON."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HISTORY_ROW_SCHEMA = "insight_survivor_health_history_row_v1"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_under_root(p: Path) -> Path:
    if p.is_absolute():
        return p
    return ROOT / p


def load_survivor_doc(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def compute_latest(survivors: list[Any]) -> dict[str, Any]:
    n = len(survivors)
    if n == 0:
        mean = 0.0
    else:
        mean = sum(float(x.get("fusion_candidate_score", 0.0)) for x in survivors) / max(1, n)
    return {"survivor_count": n, "survivor_mean_score": round(mean, 6)}


def _load_history_rows(hp: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not hp.is_file():
        return rows
    for line in hp.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except Exception:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _latest_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("schema") != HISTORY_ROW_SCHEMA:
            continue
        lat = r.get("latest")
        if isinstance(lat, dict) and "survivor_count" in lat and "survivor_mean_score" in lat:
            out.append(lat)
    return out


def _compare_latest(
    prev: dict[str, Any],
    curr: dict[str, Any],
    thr_mean: float,
    thr_count: int,
) -> tuple[bool, dict[str, float], float]:
    dc = int(curr["survivor_count"]) - int(prev["survivor_count"])
    dm = float(curr["survivor_mean_score"]) - float(prev["survivor_mean_score"])
    deltas = {"survivor_count": float(dc), "survivor_mean_score": dm}
    drift = abs(dc) >= thr_count or abs(dm) >= thr_mean
    max_abs = max(abs(float(dc)), abs(dm))
    return drift, deltas, max_abs


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _webhook_url(cli_url: str) -> str:
    return (
        (cli_url or "").strip()
        or (os.getenv("INSIGHT_SURVIVOR_HEALTH_ALERT_WEBHOOK_URL") or "").strip()
        or (os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()
    )


def _attach_webhook(
    alert: dict[str, Any],
    *,
    dry_run: bool,
    webhook_cli: str,
    hist_path: Path | None,
) -> None:
    wh_url = _webhook_url(webhook_cli)
    if dry_run:
        alert["webhook"] = {"sent": False, "status": "skipped_dry_run"}
    elif hist_path is None:
        alert["webhook"] = {"sent": False, "status": "skipped_no_history_jsonl"}
    elif alert.get("reason") == "insufficient_history":
        alert["webhook"] = {"sent": False, "status": "skipped_insufficient_history"}
    elif not alert.get("should_alert"):
        alert["webhook"] = {"sent": False, "status": "skipped_should_false"}
    elif not wh_url:
        alert["webhook"] = {"sent": False, "status": "skipped_no_url"}
    else:
        payload = {
            "event": "insight_survivor_health_alert_v1",
            "generated_at_utc": alert["generated_at_utc"],
            "reason": alert["reason"],
            "latest": alert["latest"],
            "deltas": alert.get("deltas") or {},
            "max_abs_delta": alert.get("max_abs_delta", 0.0),
            "survivor_json": str(alert.get("_survivor_json_path", "")),
        }
        ok, status = _post_webhook(wh_url, payload)
        alert["webhook"] = {"sent": ok, "status": status, "url_present": True}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Insight survivor health: latest stats vs optional JSONL history. "
            "One-click: run_aramaic_mvp_chain_v1.ps1 -SurvivorHealthAlertDryRun or env MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN; "
            "SSOT: docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md (Aramaic ops table)."
        )
    )
    ap.add_argument("--survivor-json", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument(
        "--history-jsonl",
        default="",
        help="Optional JSONL of insight_survivor_health_history_row_v1 rows (latest snapshots).",
    )
    ap.add_argument(
        "--drift-threshold-mean",
        type=float,
        default=0.05,
        help="Absolute mean-score delta that counts as drift (default 0.05).",
    )
    ap.add_argument(
        "--drift-threshold-count",
        type=int,
        default=1,
        help="Absolute survivor_count delta that counts as drift (default 1).",
    )
    ap.add_argument(
        "--append-history",
        action="store_true",
        help="Append one insight_survivor_health_history_row_v1 line (same --history-jsonl path).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Never POST webhook even if URL is set.",
    )
    ap.add_argument(
        "--webhook-url",
        default="",
        help="Override webhook URL (default: INSIGHT_SURVIVOR_HEALTH_ALERT_WEBHOOK_URL then OPS_ALARM_WEBHOOK_URL).",
    )
    a = ap.parse_args()

    sp = resolve_under_root(Path(a.survivor_json))
    op = resolve_under_root(Path(a.output_json))
    d = load_survivor_doc(sp)
    surv = list(d.get("survivors") or [])
    latest = compute_latest(surv)

    thr_mean = float(a.drift_threshold_mean)
    thr_count = max(0, int(a.drift_threshold_count))

    alert: dict[str, Any] = {
        "schema": "insight_survivor_health_alert_v1",
        "generated_at_utc": now(),
        "source_track": "T",
        "research_only": True,
        "promotion_required": True,
        "latest": latest,
        "should_alert": False,
        "reason": "insufficient_history",
        "deltas": {},
        "max_abs_delta": 0.0,
        "drift_threshold_mean": thr_mean,
        "drift_threshold_count": thr_count,
    }

    hist_path = Path(a.history_jsonl.strip()) if a.history_jsonl.strip() else None
    if hist_path is not None and not hist_path.is_absolute():
        hist_path = ROOT / hist_path

    snaps: list[dict[str, Any]] = []
    if hist_path is not None:
        snaps = _latest_snapshots(_load_history_rows(hist_path))
        alert["history_latest_snapshots"] = len(snaps)

    if not snaps:
        alert["reason"] = "insufficient_history"
        alert["should_alert"] = False
    else:
        prev = snaps[-1]
        drift, deltas, max_abs = _compare_latest(prev, latest, thr_mean, thr_count)
        alert["deltas"] = deltas
        alert["max_abs_delta"] = max_abs
        alert["prev_latest"] = prev
        if drift:
            alert["reason"] = "health_drift"
            alert["should_alert"] = True
        else:
            alert["reason"] = "stable_below_threshold"
            alert["should_alert"] = False

    alert["_survivor_json_path"] = str(sp)
    _attach_webhook(
        alert,
        dry_run=bool(a.dry_run),
        webhook_cli=str(a.webhook_url or ""),
        hist_path=hist_path,
    )
    alert.pop("_survivor_json_path", None)

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(alert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if a.append_history and hist_path is not None:
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "schema": HISTORY_ROW_SCHEMA,
            "generated_at_utc": alert["generated_at_utc"],
            "latest": latest,
        }
        with hist_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
