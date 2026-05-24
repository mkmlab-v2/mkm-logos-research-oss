#!/usr/bin/env python3
import json, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tok = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("MKM_MKMLIFE_CF_ANALYTICS_TOKEN="))
zone = "259a847ea3643566383972ebd3ede918"
end = datetime.now(timezone.utc)
start = end - timedelta(hours=24)
filt = {
    "datetime_geq": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "datetime_lt": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "requestSource": "eyeball",
    "clientRequestHTTPHost": "mkmlife.com",
    "clientRequestPath_like": "/oracle-sphere%",
}
q = """
query($zone: String!, $filter: ZoneHttpRequestsAdaptiveGroupsFilter_InputObject) {
  viewer { zones(filter: { zoneTag: $zone }) {
    httpRequestsAdaptiveGroups(limit: 5, filter: $filter, orderBy: [sum_visits_DESC]) {
      sum { visits pageViews requests }
      dimensions { clientRequestPath }
    }
  }}
}
"""
body = json.dumps({"query": q, "variables": {"zone": zone, "filter": filt}}).encode()
req = urllib.request.Request(
    "https://api.cloudflare.com/client/v4/graphql",
    data=body,
    method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=60) as r:
    d = json.loads(r.read())
if d.get("errors"):
    print("ERR", d["errors"][0].get("message"))
else:
    g = (((d.get("data") or {}).get("viewer") or {}).get("zones") or [{}])[0].get("httpRequestsAdaptiveGroups") or []
    print("rows", len(g))
    for row in g:
        print(row)
