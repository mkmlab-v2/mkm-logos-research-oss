#!/usr/bin/env python3
"""Build Logos Ask quality gate daily report (Python fallback)."""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/fixtures/logos_ask_quality_completion_contract_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_ask_quality_gate_daily_report_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/logos_ask_quality_gate_daily_report_v1_log.jsonl"

LEAK_RE = re.compile(r"lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def post_inquiry(base: str, query: str, *, timeout_s: int = 180) -> dict[str, Any]:
    payload = {
        "query": query,
        "output_format": "inquiry_report_v1",
        "domain_lane": "logos",
        "intent_chip": "reports",
        "azure_distill_mode": "auto",
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/logos-research/query",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(resp.status)
            body = resp.read().decode("utf-8-sig")
            doc = json.loads(body)
            return {"ok": status == 200 and bool(doc.get("ok", True)), "status": status, "doc": doc}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            doc = {"error": raw[:200]}
        return {"ok": False, "status": int(exc.code), "doc": doc}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "doc": {"error": str(exc)}}


def safe_rate(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 4)


def posture(summary: dict[str, Any]) -> str:
    recomposed = float(summary["format_gate"]["recomposed_rate"])
    leak = float(summary["s4_public_sanitize"]["leak_detected_rate"])
    azure = float(summary["azure_distill"]["applied_rate"])
    if recomposed <= 0.3 and leak <= 0.1 and azure >= 0.2:
        return "healthy"
    if recomposed <= 0.5 and leak <= 0.2:
        return "watch"
    return "needs_attention"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:3010")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--timeout-s", type=int, default=180, help="HTTP timeout per probe request")
    args = ap.parse_args()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    queries = contract.get("live_battery_queries") or []
    rows: list[dict[str, Any]] = []

    for item in queries:
        query = str(item.get("query_ko") or "").strip()
        response = post_inquiry(args.base, query, timeout_s=args.timeout_s)
        if not response["ok"]:
            rows.append(
                {
                    "id": item.get("id"),
                    "query_ko": query,
                    "ok": False,
                    "status": response["status"],
                    "error": response["doc"].get("error", "http_error"),
                }
            )
            continue
        doc = response["doc"]
        report = doc.get("report") or {}
        s4 = ((report.get("sections") or {}).get("S4") or {})
        gate = s4.get("format_gate") or {}
        result = doc.get("result") or {}
        az = report.get("azure_distill_meta") or result.get("azure_distill_meta") or {}
        s4_body = str(s4.get("body_ko") or "")
        rows.append(
            {
                "id": item.get("id"),
                "query_ko": query,
                "ok": True,
                "status": response["status"],
                "query_mode": report.get("query_mode") or result.get("query_mode"),
                "format_gate": {
                    "applied": bool(gate.get("applied")),
                    "recomposed": bool(gate.get("recomposed")),
                    "missing_sections_count": len(gate.get("missing_sections") or []),
                },
                "s4_public_sanitize": {
                    "leak_detected": bool(LEAK_RE.search(s4_body)),
                },
                "azure_distill_meta": {
                    "attempted": bool(az.get("attempted")),
                    "mode": str(az.get("mode") or "auto"),
                    "decision_reason": str(az.get("decision_reason") or "unknown"),
                    "decision_signal_count": int(az.get("decision_signal_count") or 0),
                    "applied": bool(az.get("applied")),
                    "failure_reason": az.get("failure_reason"),
                },
            }
        )

    ok_rows = [r for r in rows if r.get("ok")]
    ok_n = len(ok_rows)
    recomposed = sum(1 for r in ok_rows if (r.get("format_gate") or {}).get("recomposed"))
    applied = sum(1 for r in ok_rows if (r.get("format_gate") or {}).get("applied"))
    leak = sum(1 for r in ok_rows if (r.get("s4_public_sanitize") or {}).get("leak_detected"))
    az_attempt = sum(1 for r in ok_rows if (r.get("azure_distill_meta") or {}).get("attempted"))
    az_applied = sum(1 for r in ok_rows if (r.get("azure_distill_meta") or {}).get("applied"))
    reason_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    for row in ok_rows:
        reason = str((row.get("azure_distill_meta") or {}).get("decision_reason") or "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        failure = (row.get("azure_distill_meta") or {}).get("failure_reason")
        if failure:
            failure_counts[str(failure)] = failure_counts.get(str(failure), 0) + 1

    summary = {
        "probe_total": len(rows),
        "probe_http_ok": ok_n,
        "format_gate": {
            "applied_count": applied,
            "recomposed_count": recomposed,
            "recomposed_rate": safe_rate(recomposed, ok_n),
        },
        "s4_public_sanitize": {
            "leak_detected_count": leak,
            "leak_detected_rate": safe_rate(leak, ok_n),
        },
        "azure_distill": {
            "attempted_count": az_attempt,
            "applied_count": az_applied,
            "applied_rate": safe_rate(az_applied, ok_n),
            "decision_reason_counts": reason_counts,
            "failure_reason_counts": failure_counts,
        },
    }

    report = {
        "schema": "logos_ask_quality_gate_daily_report_v1",
        "generated_at_utc": utc_now(),
        "base": args.base.rstrip("/"),
        "research_only": True,
        "summary": summary,
        "posture": posture(summary),
        "rows": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.jsonl.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "posture": report["posture"],
                "recomposed_rate": summary["format_gate"]["recomposed_rate"],
                "leak_detected_rate": summary["s4_public_sanitize"]["leak_detected_rate"],
                "azure_applied_rate": summary["azure_distill"]["applied_rate"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
