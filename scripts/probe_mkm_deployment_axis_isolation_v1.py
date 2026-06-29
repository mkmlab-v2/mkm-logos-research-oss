#!/usr/bin/env python3
"""Live probe: mkmlife CF Workers vs jema-ai/logos VPS — DNS/deploy axis isolation.

Profiles:
  core     — gate for daily ops (mkmlife data wall + jema/logos host split)
  extended — core + optional cross-domain negative checks
  full     — all checks (exit gates on core only)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "mkm_deployment_axis_isolation_probe_latest.json"
HISTORY = ROOT / "reports" / "mkm_deployment_axis_isolation_probe_history.jsonl"

CHECKS: list[dict[str, Any]] = [
    {
        "id": "mkmlife_data_internal_blocked",
        "axis": "mkmlife_cf",
        "tier": "core",
        "url": "https://mkmlife.com/data/internal/three_lens_sphere_envelope_v1.json",
        "expect_status": 404,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "mkmlife_envelope_legacy_static_404",
        "axis": "mkmlife_cf",
        "tier": "core",
        "url": "https://mkmlife.com/data/three_lens_sphere_envelope_v1.json",
        "expect_status": 404,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "mkmlife_envelope_public_logos_only",
        "axis": "mkmlife_cf",
        "tier": "core",
        "url": "https://mkmlife.com/data/three_lens_sphere_envelope_public_v1.json",
        "markers": [
            '"schema": "three_lens_sphere_envelope_v1"',
            '"profile_mode": "public_logos_only"',
            '"hypothesis_tier": "B"',
        ],
        "max_bytes": 8192,
    },
    {
        "id": "mkmlife_full_envelope_api_unauth",
        "axis": "mkmlife_cf",
        "tier": "core",
        "url": "https://mkmlife.com/api/v1/oracle-sphere/full-envelope",
        "expect_status": 403,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "mkmlife_oracle_sphere_consumer",
        "axis": "mkmlife_cf",
        "tier": "core",
        "url": "https://mkmlife.com/oracle-sphere",
        "markers": ["magic-orb-page", "관측 구"],
        "forbid_markers": ["마법구슬"],
        "max_bytes": 65536,
    },
    {
        "id": "jema_app_logos_research_canonical_redirect",
        "axis": "jema_logos_dns",
        "tier": "core",
        "url": "https://app.jema-ai.com/logos-research",
        "expect_status": 308,
        "expect_location_contains": "logos.jema-ai.com",
        "no_redirect": True,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "jema_apex_logos_research_hops_to_logos",
        "axis": "jema_logos_dns",
        "tier": "extended",
        "url": "https://jema-ai.com/logos-research",
        "follow_redirects": True,
        "expect_final_host": "logos.jema-ai.com",
        "markers": ["logos-research-page"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "logos_subdomain_workspace_root",
        "axis": "jema_logos_dns",
        "tier": "core",
        "url": "https://logos.jema-ai.com/",
        "markers": ["logos-research-page", "logos-research"],
        "max_bytes": 65536,
    },
    {
        "id": "jema_app_oracle_sphere_not_mkmlife",
        "axis": "jema_logos_dns",
        "tier": "core",
        "url": "https://app.jema-ai.com/oracle-sphere",
        "forbid_markers": ["magic-orb-page", "magic-orb-disclaimer"],
        "max_bytes": 65536,
        "optional": False,
    },
    {
        "id": "jema_hub_oracle_sphere_not_mkmlife",
        "axis": "jema_logos_dns",
        "tier": "extended",
        "url": "https://jema-ai.com/oracle-sphere",
        "forbid_markers": ["magic-orb-page"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "logos_not_serving_mkmlife_magic_orb_json",
        "axis": "jema_logos_dns",
        "tier": "extended",
        "url": "https://logos.jema-ai.com/data/magic_orb_hero_slices_v1.json",
        "expect_status": 404,
        "markers": [],
        "max_bytes": 512,
        "optional": True,
    },
]

PROFILE_TIERS = {
    "core": {"core"},
    "extended": {"core", "extended"},
    "full": {"core", "extended"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(
    url: str,
    *,
    timeout: int = 25,
    max_bytes: int = 4096,
    no_redirect: bool = False,
    follow_redirects: bool = False,
) -> tuple[int | None, str, dict[str, str], str | None, str | None]:
    handlers: list[urllib.request.BaseHandler] = []
    if no_redirect:
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
                return None

        handlers.append(_NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-probe-deployment-axis/1.0"})
    final_url: str | None = None
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(max_bytes).decode("utf-8", errors="replace")
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            final_url = resp.geturl()
            return resp.status, body, hdrs, None, final_url
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        hdrs = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return exc.code, body, hdrs, None, exc.geturl() if follow_redirects else None
    except Exception as exc:
        return None, "", {}, str(exc), None


def _tier_ok(results: list[dict], tier: str) -> bool:
    rows = [r for r in results if r.get("tier") == tier]
    return bool(rows) and all(r["ok"] for r in rows)


def run_probe(*, profile: str, out_path: Path) -> tuple[dict, int]:
    tiers = PROFILE_TIERS.get(profile)
    if not tiers:
        raise SystemExit(f"unknown profile: {profile}")

    results: list[dict] = []
    for row in CHECKS:
        if row.get("tier") not in tiers:
            continue
        max_b = int(row.get("max_bytes") or 4096)
        status, body, hdrs, err, final_url = _fetch(
            row["url"],
            max_bytes=max_b,
            no_redirect=bool(row.get("no_redirect")),
            follow_redirects=bool(row.get("follow_redirects")),
        )
        missing = [m for m in row.get("markers") or [] if m not in body]
        forbidden = [m for m in row.get("forbid_markers") or [] if m in body]
        expect_status = row.get("expect_status")
        location = hdrs.get("location", "")
        expect_loc = row.get("expect_location_contains")
        expect_final_host = row.get("expect_final_host")

        if expect_final_host:
            from urllib.parse import urlparse

            host = urlparse(final_url or row["url"]).hostname or ""
            core_ok = host == expect_final_host
            markers_ok = not missing
        elif expect_status is not None:
            core_ok = status == expect_status
            if expect_loc:
                core_ok = core_ok and expect_loc in location
            markers_ok = True
        elif row.get("forbid_markers") and not (row.get("markers") or []):
            core_ok = status is not None
            markers_ok = not forbidden
        else:
            core_ok = status is not None and 200 <= status < 400 and err is None
            markers_ok = not missing and not forbidden

        optional = bool(row.get("optional"))
        ok = core_ok and (markers_ok or optional)
        results.append(
            {
                "id": row["id"],
                "axis": row.get("axis"),
                "tier": row.get("tier"),
                "url": row["url"],
                "status": status,
                "location": location or None,
                "final_url": final_url,
                "markers": row.get("markers") or [],
                "missing_markers": missing,
                "forbidden_markers": forbidden,
                "optional": optional,
                "ok": ok,
                "error": err,
            }
        )

    core_all_ok = _tier_ok(results, "core")
    extended_all_ok = _tier_ok(results, "extended") if "extended" in tiers else True
    mkmlife_ok = all(r["ok"] for r in results if r.get("axis") == "mkmlife_cf")
    jema_logos_ok = all(r["ok"] for r in results if r.get("axis") == "jema_logos_dns")

    if profile == "core":
        gate_ok = core_all_ok
    elif profile == "extended":
        gate_ok = core_all_ok and extended_all_ok
    else:
        gate_ok = core_all_ok

    doc = {
        "schema": "mkm_deployment_axis_isolation_probe_v1",
        "profile": profile,
        "checked_at_utc": _now(),
        "verdict_ko": "격벽 probe OK" if gate_ok else "격벽 probe 실패",
        "core_all_ok": core_all_ok,
        "extended_all_ok": extended_all_ok,
        "mkmlife_cf_ok": mkmlife_ok,
        "jema_logos_dns_ok": jema_logos_ok,
        "all_ok": gate_ok,
        "track_wall": {"hypothesis_tier": "B", "research_only": True, "send_gate": "HOLD"},
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history_row = {
        "checked_at_utc": doc["checked_at_utc"],
        "profile": profile,
        "all_ok": gate_ok,
        "mkmlife_cf_ok": mkmlife_ok,
        "jema_logos_dns_ok": jema_logos_ok,
        "verdict_ko": doc["verdict_ko"],
        "results": [{"id": r["id"], "axis": r.get("axis"), "status": r["status"], "ok": r["ok"]} for r in results],
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(history_row, ensure_ascii=False) + "\n")

    return doc, 0 if gate_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILE_TIERS),
        default="core",
        help="Which probe tiers to run and gate on (default: core).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc, code = run_probe(profile=args.profile, out_path=args.out)
    rel = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"Wrote {rel} profile={args.profile} all_ok={doc['all_ok']}")
    print(f"Appended {HISTORY.relative_to(ROOT)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
