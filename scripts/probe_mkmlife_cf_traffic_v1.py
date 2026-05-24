#!/usr/bin/env python3
"""Optional mkmlife.com Cloudflare zone analytics snapshot (UV/requests proxy). Skips if token missing."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZONE_FIXTURE = ROOT / "scripts/data/hostinger_full_exit/mkmlife_cloudflare_zone_v1.json"
OUT = ROOT / "reports/mkmlife_cf_traffic_probe_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_token() -> tuple[str, str | None]:
    """Return (token, source_env_key). Prefer mkmlife analytics-specific env."""
    keys = (
        "MKM_MKMLIFE_CF_ANALYTICS_TOKEN",
        "MKM_CLOUDFLARE_ANALYTICS_TOKEN",
        "CLOUDFLARE_API_TOKEN",
        "CF_API_TOKEN",
    )

    def _parse_env_file() -> dict[str, str]:
        env_path = ROOT / ".env"
        found: dict[str, str] = {}
        if not env_path.is_file():
            return found
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k in keys:
                found[k] = v.strip().strip('"').strip("'")
        return found

    # .env first — avoids stale Process CLOUDFLARE_API_TOKEN shadowing MKM_MKMLIFE_CF_ANALYTICS_TOKEN.
    for key in keys:
        val = (_parse_env_file().get(key) or "").strip()
        if val:
            return val, f".env:{key}"
    for key in keys:
        val = (os.environ.get(key) or "").strip()
        if val:
            return val, key
    return "", None


def _graphql(tok: str, zone_id: str) -> dict:
    now = datetime.now(timezone.utc)
    query = """
    query MkmlifeZoneDay($zone: String!, $dateToday: Date!, $dateYesterday: Date!) {
      viewer {
        zones(filter: { zoneTag: $zone }) {
          httpRequests1dGroups(limit: 2, filter: { date_geq: $dateYesterday, date_leq: $dateToday }) {
            dimensions { date }
            sum { requests pageViews }
            uniq { uniques }
          }
        }
      }
    }
    """
    body = {
        "query": query,
        "variables": {
            "zone": zone_id,
            "dateToday": now.date().isoformat(),
            "dateYesterday": (now.date() - timedelta(days=1)).isoformat(),
        },
    }
    url = "https://api.cloudflare.com/client/v4/graphql"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode())
        except Exception:
            return {"success": False, "errors": [{"message": str(exc), "code": exc.code}]}


def _graphql_path_visits(
    tok: str, zone_id: str, *, path_prefix: str = "/oracle-sphere", hours: int = 24
) -> dict:
    """Adaptive groups rollup for path prefix (eyeball, mkmlife host)."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    query = """
    query MkmlifePath($zone: String!, $filter: ZoneHttpRequestsAdaptiveGroupsFilter_InputObject) {
      viewer {
        zones(filter: { zoneTag: $zone }) {
          httpRequestsAdaptiveGroups(
            limit: 10
            filter: $filter
            orderBy: [sum_visits_DESC]
          ) {
            sum { visits }
            dimensions { clientRequestPath }
          }
        }
      }
    }
    """
    filt = {
        "datetime_geq": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datetime_lt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requestSource": "eyeball",
        "clientRequestHTTPHost": "mkmlife.com",
        "clientRequestPath_like": f"{path_prefix}%",
    }
    body = {"query": query, "variables": {"zone": zone_id, "filter": filt}}
    url = "https://api.cloudflare.com/client/v4/graphql"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
        except Exception:
            return {"ok": False, "errors": [{"message": str(exc)}]}
    if payload.get("errors"):
        return {"ok": False, "errors": payload.get("errors")}
    zones = (((payload.get("data") or {}).get("viewer") or {}).get("zones")) or []
    groups = (zones[0] or {}).get("httpRequestsAdaptiveGroups") or [] if zones else []
    visits = sum(int((g.get("sum") or {}).get("visits") or 0) for g in groups)
    paths = [
        (g.get("dimensions") or {}).get("clientRequestPath")
        for g in groups
        if (g.get("dimensions") or {}).get("clientRequestPath")
    ]
    return {
        "ok": True,
        "path_prefix": path_prefix,
        "hours": hours,
        "visits": visits,
        "path_rows": len(groups),
        "paths_sample": paths[:10],
        "source": "graphql_httpRequestsAdaptiveGroups_path_like",
    }


def _api(tok: str, path: str) -> dict:
    url = f"https://api.cloudflare.com/client/v4{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode())
        except Exception:
            return {"success": False, "errors": [{"message": str(exc), "code": exc.code}]}


def main() -> int:
    zone_id = None
    apex = "mkmlife.com"
    if ZONE_FIXTURE.is_file():
        fx = json.loads(ZONE_FIXTURE.read_text(encoding="utf-8"))
        zone_id = fx.get("zone_id")
        apex = fx.get("apex") or apex

    tok, tok_source = _load_token()
    doc: dict = {
        "schema": "mkmlife_cf_traffic_probe_v1",
        "generated_at_utc": _utc_now(),
        "apex": apex,
        "zone_id": zone_id,
        "token_present": bool(tok),
        "token_source_env": tok_source,
        "zone_read_ok": None,
        "cf_analytics_fetched": False,
        "payment_e2e_deferred": True,
        "track_wall": {"hypothesis_tier": "B", "research_only": True},
    }

    if not tok:
        doc["skipped_reason"] = "CLOUDFLARE_API_TOKEN missing — set in .env or User env"
        doc["dashboard_url_ko"] = f"https://dash.cloudflare.com → {apex} → Analytics"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT.relative_to(ROOT)} skipped=token_missing")
        return 0

    if not zone_id:
        doc["skipped_reason"] = "zone_id missing in mkmlife_cloudflare_zone_v1.json"
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT.relative_to(ROOT)} skipped=no_zone_id")
        return 0

    zone_payload = _api(tok, f"/zones/{zone_id}")
    doc["zone_read_ok"] = bool(zone_payload.get("success"))

    # GraphQL zone rollup (preferred when Analytics:Read on mkmlife zone)
    gql = _graphql(tok, zone_id)
    gql_ok = not (gql.get("errors") or [])
    zones = (((gql.get("data") or {}).get("viewer") or {}).get("zones")) or []
    if gql_ok and zones:
        groups = (zones[0] or {}).get("httpRequests1dGroups") or []
        if groups:
            row = groups[0]
            sums = row.get("sum") or {}
            uniq = row.get("uniq") or {}
            doc["last_24h"] = {
                "date": (row.get("dimensions") or {}).get("date"),
                "requests": sums.get("requests"),
                "page_views": sums.get("pageViews"),
                "unique_visitors": uniq.get("uniques"),
                "source": "graphql_httpRequests1dGroups",
            }
            doc["cf_analytics_fetched"] = True

    if doc["cf_analytics_fetched"] and tok and zone_id:
        path_roll = _graphql_path_visits(tok, zone_id)
        if path_roll.get("ok"):
            doc["oracle_sphere_path_24h"] = path_roll
        else:
            doc["oracle_sphere_path_24h"] = {
                "ok": False,
                "errors": path_roll.get("errors"),
            }

    if not doc["cf_analytics_fetched"]:
        doc["api_errors"] = gql.get("errors") or zone_payload.get("errors") or [{"message": "unknown"}]
        doc["skipped_reason"] = (
            "CF analytics unavailable — use MKM_MKMLIFE_CF_ANALYTICS_TOKEN with Zone Analytics Read on mkmlife.com"
            if not doc["zone_read_ok"]
            else "token lacks Analytics Read for mkmlife zone"
        )
        doc["dashboard_url_ko"] = f"https://dash.cloudflare.com → zone {apex} → Analytics → Traffic → filter /oracle-sphere"

    doc["oracle_sphere_path_hint"] = "/oracle-sphere"
    doc["observability_note_ko"] = (
        "Zone rollup + optional oracle_sphere_path_24h (GraphQL path_like). "
        "live probe 가용성은 magic_orb_open_beta_traffic_summary_latest.json."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} fetched={doc['cf_analytics_fetched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
