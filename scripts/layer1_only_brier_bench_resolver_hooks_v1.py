"""External resolver probe hooks for Layer-1-only Brier bench PoC (B-track)."""
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import parse, request

from layer1_only_brier_bench_poc_lib_v1 import deadline_reached, load_dotenv_if_present

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MKM-Layer1-Brier-PoC/1.0"
)
OECD_FORESIGHT_CANDIDATE_URLS = (
    "https://www.oecd.org/en/publications/foresight-toolkit-for-responsible-policy-making_b89d1c4d-en.html",
    "https://www.oecd.org/governance/foresight/",
    "https://www.oecd.org/en/search.html?search=Foresight+Toolkit",
)
PYTHON_RELEASE_CANDIDATE_URLS = (
    "https://www.python.org/downloads/",
    "https://www.python.org/doc/versions/",
)


def http_get(
    url: str,
    *,
    timeout: int = 30,
    max_bytes: int = 262144,
    retries: int = 2,
) -> dict[str, Any]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last: dict[str, Any] = {"ok": False, "status": 0, "error": "no attempt"}
    for attempt in range(retries + 1):
        req = request.Request(url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                body = resp.read(max_bytes).decode("utf-8", errors="replace")
                return {
                    "ok": True,
                    "status": resp.status,
                    "body": body,
                    "body_preview": body[:800],
                    "attempt": attempt + 1,
                }
        except Exception as e:
            code = getattr(e, "code", 0)
            last = {
                "ok": False,
                "status": int(code or 0),
                "error": str(e),
                "body": "",
                "body_preview": "",
                "attempt": attempt + 1,
            }
            if attempt >= retries:
                return last
    return last


def fred_unrate_observations(*, api_key: str, limit: int = 24) -> list[dict[str, str]]:
    q = parse.urlencode(
        {
            "series_id": "UNRATE",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows: list[dict[str, str]] = []
    for row in doc.get("observations") or []:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")
        v = str(row.get("value") or "").strip()
        if v and v != ".":
            rows.append({"date": d, "value": v})
    return rows


def fred_ecb_mro_observations(*, api_key: str, limit: int = 48) -> list[dict[str, str]]:
    q = parse.urlencode(
        {
            "series_id": "ECBMAIN",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows: list[dict[str, str]] = []
    for row in doc.get("observations") or []:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")
        v = str(row.get("value") or "").strip()
        if v and v != ".":
            rows.append({"date": d, "value": v})
    return rows


def probe_bls_u3_below_4pct(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    qid = row.get("question_id")
    evidence = "https://www.bls.gov/news.release/empsit.nr0.htm"
    if not live:
        return {
            "probe_kind": "official_statistics",
            "authority": "bls.gov",
            "status": "dry_run",
            "series": "UNRATE",
        }
    load_dotenv_if_present()
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return {
            "probe_kind": "official_statistics",
            "authority": "bls.gov",
            "status": "holdout_pending",
            "reason": "FRED_API_KEY missing; manual BLS resolve only",
            "evidence_uri": evidence,
        }
    try:
        obs = fred_unrate_observations(api_key=api_key)
    except Exception as e:
        return {
            "probe_kind": "official_statistics",
            "authority": "bls.gov",
            "status": "probe_inconclusive",
            "error": str(e),
            "evidence_uri": evidence,
        }
    rows_2026 = [r for r in obs if str(r.get("date", "")).startswith("2026-")]
    below = [r for r in rows_2026 if float(r["value"]) < 4.0]
    interim = {
        "fred_rows_2026": rows_2026,
        "any_month_below_4pct": bool(below),
    }
    if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
        return {
            "probe_kind": "official_statistics",
            "authority": "bls.gov",
            "status": "holdout_pending",
            "reason": "deadline not reached",
            "interim": interim,
            "evidence_uri": evidence,
        }
    outcome = 1 if below else 0
    return {
        "probe_kind": "official_statistics",
        "authority": "bls.gov",
        "status": "resolved_candidate",
        "outcome": outcome,
        "interim": interim,
        "evidence_uri": evidence,
        "resolver_notes": f"{qid}: any 2026 UNRATE < 4.0 => {bool(below)}",
    }


def probe_ecb_mro_above_3_5(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    evidence = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"
    if not live:
        return {"probe_kind": "official_statistics", "authority": "ecb.europa.eu", "status": "dry_run"}
    load_dotenv_if_present()
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    rows_2026: list[dict[str, str]] = []
    if api_key:
        try:
            obs = fred_ecb_mro_observations(api_key=api_key)
            rows_2026 = [r for r in obs if str(r.get("date", "")).startswith("2026-")]
        except Exception:
            rows_2026 = []
    if not rows_2026:
        page = http_get(evidence)
        if not page.get("ok"):
            return {
                "probe_kind": "official_statistics",
                "authority": "ecb.europa.eu",
                "status": "probe_inconclusive",
                "error": page.get("error"),
                "evidence_uri": evidence,
            }
        nums = [float(x) for x in re.findall(r"\b([23]\.\d{2})\b", page.get("body") or "")]
        above = [n for n in nums if n > 3.50]
        interim = {"html_rate_samples": nums[:20], "any_sample_above_3_5": bool(above)}
        if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
            return {
                "probe_kind": "official_statistics",
                "authority": "ecb.europa.eu",
                "status": "holdout_pending",
                "reason": "deadline not reached",
                "interim": interim,
                "evidence_uri": evidence,
                "data_source": "ecb_html_heuristic_v1",
            }
        return {
            "probe_kind": "official_statistics",
            "authority": "ecb.europa.eu",
            "status": "resolved_candidate",
            "outcome": 1 if above else 0,
            "interim": interim,
            "evidence_uri": evidence,
            "data_source": "ecb_html_heuristic_v1",
        }
    above = [r for r in rows_2026 if float(r["value"]) > 3.50]
    interim = {"fred_ecbmain_2026": rows_2026, "any_above_3_5": bool(above)}
    if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
        return {
            "probe_kind": "official_statistics",
            "authority": "ecb.europa.eu",
            "status": "holdout_pending",
            "reason": "deadline not reached",
            "interim": interim,
            "evidence_uri": evidence,
            "data_source": "fred_ecbmain",
        }
    return {
        "probe_kind": "official_statistics",
        "authority": "ecb.europa.eu",
        "status": "resolved_candidate",
        "outcome": 1 if above else 0,
        "interim": interim,
        "evidence_uri": evidence,
        "data_source": "fred_ecbmain",
    }


def _count_distinct_headings(html: str) -> int:
    headings = re.findall(
        r"(?:<h[1-6][^>]*>|^|\n)\s*(?:Chapter|Section|Part)\s+[\dIVXLC]+[\:\.\-\s]+([^\n<]{4,80})",
        html,
        flags=re.IGNORECASE,
    )
    toc_lines = re.findall(r"(?:^|\n)\s*\d+(?:\.\d+)*\s+([A-Z][^\n]{8,80})", html)
    uniq = {h.strip().lower() for h in headings + toc_lines if h.strip()}
    return len(uniq)


def probe_oecd_foresight_headings(row: dict[str, Any], *, live: bool) -> dict[str, Any]:
    if not live:
        return {"probe_kind": "document_structure", "authority": "oecd.org", "status": "dry_run"}

    fetch_attempts: list[dict[str, Any]] = []
    body = ""
    evidence = OECD_FORESIGHT_CANDIDATE_URLS[-1]
    for url in OECD_FORESIGHT_CANDIDATE_URLS:
        result = http_get(url)
        fetch_attempts.append(
            {
                "url": url,
                "ok": result.get("ok"),
                "status": result.get("status"),
                "error": result.get("error"),
            }
        )
        if result.get("ok"):
            body = result.get("body") or ""
            evidence = url
            break

    if not body:
        if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
            return {
                "probe_kind": "document_structure",
                "authority": "oecd.org",
                "status": "holdout_pending",
                "reason": "source fetch blocked; interim unavailable",
                "fetch_attempts": fetch_attempts,
                "evidence_uri": evidence,
            }
        return {
            "probe_kind": "document_structure",
            "authority": "oecd.org",
            "status": "probe_inconclusive",
            "error": "all candidate URLs failed",
            "fetch_attempts": fetch_attempts,
            "evidence_uri": evidence,
        }

    toolkit_links = re.findall(
        r'href="(/en/publications/[^"]*foresight[^"]*)"',
        body,
        flags=re.IGNORECASE,
    )
    heading_count = _count_distinct_headings(body)
    interim = {
        "evidence_url": evidence,
        "fetch_attempts": fetch_attempts,
        "toolkit_link_count": len(set(toolkit_links)),
        "page_heading_like_count": heading_count,
    }
    if not deadline_reached(str(row.get("resolution_deadline_utc") or "")):
        return {
            "probe_kind": "document_structure",
            "authority": "oecd.org",
            "status": "holdout_pending",
            "reason": "deadline not reached",
            "interim": interim,
            "evidence_uri": evidence,
        }
    outcome = 1 if heading_count >= 5 else 0
    if toolkit_links:
        pub_url = "https://www.oecd.org" + toolkit_links[0]
        pub = http_get(pub_url)
        if pub.get("ok"):
            pub_count = _count_distinct_headings(pub.get("body") or "")
            interim["publication_heading_like_count"] = pub_count
            outcome = 1 if pub_count >= 5 else 0
            evidence = pub_url
    return {
        "probe_kind": "document_structure",
        "authority": "oecd.org",
        "status": "resolved_candidate",
        "outcome": outcome,
        "interim": interim,
        "evidence_uri": evidence,
        "data_source": "oecd_publication_html_heuristic_v1",
    }
