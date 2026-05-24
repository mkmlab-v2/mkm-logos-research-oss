#!/usr/bin/env python3
"""Weekly open-beta rollup from probe history + latest summary (ops handoff MD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "reports" / "magic_orb_live_probe_history.jsonl"
SUMMARY = ROOT / "reports" / "magic_orb_open_beta_traffic_summary_latest.json"
DEFAULT_JSON = ROOT / "reports/magic_orb_open_beta_weekly_rollup_latest.json"
DEFAULT_MD = ROOT / "reports/magic_orb_open_beta_weekly_rollup_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_history(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-jsonl", type=Path, default=HISTORY)
    ap.add_argument("--summary-json", type=Path, default=SUMMARY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    hist_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    sum_path = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md

    rows = _load_history(hist_path)
    summary = None
    if sum_path.is_file():
        summary = json.loads(sum_path.read_text(encoding="utf-8"))

    cf = (summary or {}).get("cf_zone_probe") or {}
    windows = (summary or {}).get("windows") or {}
    w7 = windows.get("last_7d") or {}

    doc = {
        "schema": "magic_orb_open_beta_weekly_rollup_v1",
        "generated_at_utc": _utc_now(),
        "open_beta_phase": True,
        "payment_e2e_deferred": True,
        "probe_history_entries": len(rows),
        "streak_all_ok": (summary or {}).get("streak_all_ok_from_latest"),
        "last_7d_all_ok_rate": w7.get("all_ok_rate"),
        "envelope_final_action": None,
        "cf_analytics_fetched": cf.get("cf_analytics_fetched"),
        "cf_zone_read_ok": cf.get("zone_read_ok"),
        "next_ops_ko": [
            "일상: Invoke-Op30AutoRun_v1.ps1 (Task MKM_Op30_MagicOrb_Envelope_Daily 07:50)",
            "CF UV: MKM_MKMLIFE_CF_ANALYTICS_TOKEN 또는 대시보드 수동",
            "결제 E2E: 후순위",
        ],
        "summary_pointer": str(sum_path.relative_to(ROOT)).replace("\\", "/") if sum_path.is_file() else None,
    }
    env = (summary or {}).get("latest_probe")
    if isinstance(env, dict):
        pass
    latest_env_path = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
    if latest_env_path.is_file():
        doc["envelope_final_action"] = json.loads(latest_env_path.read_text(encoding="utf-8")).get(
            "final_action"
        )

    cf24 = (cf.get("last_24h") or {}) if isinstance(cf, dict) else {}
    lines = [
        "# Magic orb open-beta weekly rollup",
        "",
        f"- generated_at_utc: {doc['generated_at_utc']}",
        f"- probe_history_entries: {doc['probe_history_entries']}",
        f"- streak_all_ok: {doc['streak_all_ok']}",
        f"- last_7d_all_ok_rate: {doc['last_7d_all_ok_rate']}",
        f"- envelope_final_action: {doc['envelope_final_action']} `[HYPO]`",
        f"- cf_analytics_fetched: {doc['cf_analytics_fetched']} (zone_read_ok={doc['cf_zone_read_ok']})",
    ]
    if cf24:
        lines.extend(
            [
                f"- cf_zone_24h_requests: {cf24.get('requests')}",
                f"- cf_zone_24h_page_views: {cf24.get('page_views')}",
                f"- cf_zone_24h_unique_visitors: {cf24.get('unique_visitors')}",
                f"- cf_source: {cf24.get('source')}",
            ]
        )
    lines.extend(["", "## Next ops", ""])
    for item in doc["next_ops_ko"]:
        lines.append(f"- {item}")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
