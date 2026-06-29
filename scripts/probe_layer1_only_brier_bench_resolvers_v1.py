#!/usr/bin/env python3
"""Probe external resolvers for Layer-1-only Brier bench PoC questions (B rail).

Live probes run only when --live and deadline criteria allow definitive resolution.
Before deadline: status holdout_pending (no outcome fabrication).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from layer1_only_brier_bench_poc_lib_v1 import (
    DEFAULT_COHORT,
    deadline_reached,
    fred_api_key_configured,
    load_cohort,
    load_dotenv_if_present,
    utc_now,
)
from layer1_only_brier_bench_resolver_hooks_v1 import (
    http_get,
    probe_bls_u3_below_4pct,
    probe_ecb_mro_above_3_5,
    probe_oecd_foresight_headings,
    PYTHON_RELEASE_CANDIDATE_URLS,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "layer1_only_brier_bench_resolver_probe_v1_latest.json"


def _probe_http_2xx(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    resolver = row.get("resolver") or {}
    endpoint = resolver.get("endpoint")
    if not isinstance(endpoint, str):
        return {"probe_kind": "http_probe", "status": "error", "reason": "missing endpoint"}
    if not live:
        return {"probe_kind": "http_probe", "status": "dry_run", "endpoint": endpoint}
    if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
        return {
            "probe_kind": "http_probe",
            "status": "holdout_pending",
            "reason": "resolution window not reached",
            "endpoint": endpoint,
        }
    result = http_get(endpoint)
    status_code = int(result.get("status") or 0)
    if not status_code:
        return {
            "probe_kind": "http_probe",
            "status": "probe_inconclusive",
            "endpoint": endpoint,
            "http_status": status_code,
            "evidence_uri": endpoint,
        }
    outcome = 1 if 200 <= status_code < 300 else 0
    return {
        "probe_kind": "http_probe",
        "status": "resolved_candidate",
        "endpoint": endpoint,
        "http_status": status_code,
        "outcome": outcome,
        "evidence_uri": endpoint,
    }


def _probe_python314(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    urls = list(PYTHON_RELEASE_CANDIDATE_URLS)
    if not live:
        return {
            "probe_kind": "official_release_index",
            "status": "dry_run",
            "url": urls[0],
            "candidate_urls": urls,
        }

    fetch_attempts: list[dict[str, Any]] = []
    body = ""
    evidence = urls[0]
    for url in urls:
        result = http_get(url, timeout=45, retries=2)
        fetch_attempts.append(
            {
                "url": url,
                "ok": result.get("ok"),
                "status": result.get("status"),
                "error": result.get("error"),
            }
        )
        if result.get("ok"):
            body = str(result.get("body") or "")
            evidence = url
            break

    if not body:
        pending = not deadline_reached(str(row.get("resolution_deadline_utc") or ""))
        return {
            "probe_kind": "official_release_index",
            "status": "holdout_pending" if pending else "probe_inconclusive",
            "reason": "fetch failed" if pending else None,
            "url": evidence,
            "candidate_urls": urls,
            "fetch_attempts": fetch_attempts,
            "error": fetch_attempts[-1].get("error") if fetch_attempts else "no attempt",
            "http_status": fetch_attempts[-1].get("status") if fetch_attempts else 0,
        }

    has_final = bool(
        re.search(
            r"Python 3\.14(?:\.\d+)?(?!.*[aA][bB]|.*[rR][cC]|.*[aA]lpha|.*[bB]eta)",
            body,
        )
    )
    if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
        return {
            "probe_kind": "official_release_index",
            "status": "holdout_pending",
            "reason": "deadline not reached",
            "interim_py314_final_seen": has_final,
            "url": evidence,
            "candidate_urls": urls,
            "fetch_attempts": fetch_attempts,
        }
    return {
        "probe_kind": "official_release_index",
        "status": "resolved_candidate",
        "url": evidence,
        "candidate_urls": urls,
        "fetch_attempts": fetch_attempts,
        "outcome": 1 if has_final else 0,
        "evidence_uri": evidence,
    }


def _probe_deferred(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    resolver = row.get("resolver") or {}
    return {
        "probe_kind": str(resolver.get("kind") or "deferred"),
        "status": "dry_run" if not live else "holdout_pending",
        "reason": "unsupported resolver hook",
        "authority": resolver.get("authority"),
    }


def probe_cohort(cohort: dict[str, Any], *, live: bool) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    for row in cohort["forecasts"]:
        qid = str(row.get("question_id") or "")
        resolver = row.get("resolver") or {}
        kind = str(resolver.get("kind") or "")
        authority = str(resolver.get("authority") or "")
        if kind == "http_probe":
            probe = _probe_http_2xx(row, live=live)
        elif kind == "official_release_index":
            probe = _probe_python314(row, live=live)
        elif kind == "official_statistics" and authority == "bls.gov":
            probe = probe_bls_u3_below_4pct(row, live=live)
        elif kind == "official_statistics" and authority == "ecb.europa.eu":
            probe = probe_ecb_mro_above_3_5(row, live=live)
        elif kind == "document_structure":
            probe = probe_oecd_foresight_headings(row, live=live)
        else:
            probe = _probe_deferred(row, live=live)
        probe["question_id"] = qid
        probe["resolution_deadline_utc"] = row.get("resolution_deadline_utc")
        probes.append(probe)

    resolved_candidates = [p for p in probes if p.get("status") == "resolved_candidate" and p.get("outcome") in (0, 1)]
    return {
        "schema": "layer1_only_brier_bench_resolver_probe_v1",
        "generated_at_utc": utc_now(),
        "track_wall": "B",
        "auto_bridge_to_a": False,
        "live": live,
        "fred_api_key_configured": fred_api_key_configured(),
        "probes": probes,
        "resolved_candidate_count": len(resolved_candidates),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--live", action="store_true", help="Run network probes (still holdout-safe before deadline).")
    ns = ap.parse_args()

    try:
        load_dotenv_if_present()
        cohort = load_cohort(ns.cohort)
        report = probe_cohort(cohort, live=ns.live)
    except ValueError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    print(f"probe report written to {ns.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
