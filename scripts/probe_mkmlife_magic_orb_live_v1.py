#!/usr/bin/env python3
"""Live probe: mkmlife oracle-sphere + envelope JSON + optional extended rows.

Design/UX is a separate axis: run `scripts/run_magic_orb_design_readiness_chain_v1.py`
and read `reports/magic_orb_design_readiness_v1_latest.json` before holistic 「잘 됨」 claims.

Profiles:
  core          — gate for daily ops (exit 1 if core tier fails)
  extended      — core + extended tier (legacy hubs, gold by-query rows)
  full          — all checks (default write; exit uses core tier only)
  job_four_slot — job four-slot by-query + API only
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "magic_orb_live_probe_latest.json"
HISTORY = ROOT / "reports" / "magic_orb_live_probe_history.jsonl"

JOB_HASH = "dc73c2c367199e48"
JOB_QUERY = "욥이 고난을 받은 이유"

CHECKS = [
    {
        "id": "mkmlife_oracle",
        "tier": "core",
        "url": "https://mkmlife.com/oracle-sphere",
        "markers": ["magic-orb-page", "관측 구", "NON-MEDICAL"],
        "markers_any": [
            ["magic-orb-disclaimer", "magic-orb-immersive-legal-line"],
            ["magic-orb-meta-arch", "Cosmic Meta-Architecture"],
        ],
        "forbid_markers": ["마법구슬", "Fact-Lock 100%"],
        "max_bytes": 65536,
    },
    {
        "id": "mkmlife_oracle_preset_job",
        "tier": "job_four_slot",
        "url": "https://mkmlife.com/oracle-sphere?preset=job_suffering_reason",
        "markers": ["magic-orb-page", "관측 구"],
        "forbid_markers": ["마법구슬", "Fact-Lock 100%"],
        "max_bytes": 65536,
    },
    {
        "id": "mkmlife_envelope_public",
        "tier": "core",
        "url": "https://mkmlife.com/data/three_lens_sphere_envelope_public_v1.json",
        "markers": [
            '"schema": "three_lens_sphere_envelope_v1"',
            '"profile_mode": "public_logos_only"',
            '"hypothesis_tier": "B"',
            "jemaai_research_shadow_lane_v3",
        ],
        "max_bytes": 8192,
    },
    {
        "id": "mkmlife_envelope_legacy_404",
        "tier": "core",
        "url": "https://mkmlife.com/data/three_lens_sphere_envelope_v1.json",
        "expect_status": 404,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "mkmlife_full_envelope_api_unauth",
        "tier": "core",
        "url": "https://mkmlife.com/api/v1/oracle-sphere/full-envelope",
        "expect_status": 403,
        "markers": [],
        "max_bytes": 512,
    },
    {
        "id": "mkmlife_home",
        "tier": "extended",
        "url": "https://mkmlife.com/",
        "markers": ["oracle-sphere", "/oracle-sphere"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "jemaai_v6",
        "tier": "extended",
        "url": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
        "markers": ["oracle-sphere", "Topology"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_latest_static",
        "tier": "core",
        "url": "https://mkmlife.com/data/magic_orb_question_insight_v1_latest.json",
        "markers": [
            '"schema": "magic_orb_question_insight_v1"',
            '"schema": "magic_orb_graph_bloom_v1"',
            '"graph_bloom"',
            '"integrity_tier"',
            '"edge_integrity_policy"',
            '"magic_orb_graph_bloom_edge_integrity_v1"',
        ],
        "max_bytes": 98304,
    },
    {
        "id": "mkmlife_hero_slices_static",
        "tier": "core",
        "url": "https://mkmlife.com/data/magic_orb_hero_slices_v1.json",
        "markers": [
            '"schema": "magic_orb_hero_slices_v1"',
            '"SYNOPTIC_PASSION_WEEK_v1"',
            '"DAN2_CLUSTER_v1"',
            '"integrity_tier"',
            '"parallel_evidence"',
        ],
        "max_bytes": 98304,
    },
    {
        "id": "mkmlife_drilldown_shards_static",
        "tier": "core",
        "url": "https://mkmlife.com/data/magic_orb_drilldown_shards_v1.json",
        "markers": [
            '"schema": "magic_orb_drilldown_shards_v1"',
            '"SYNOPTIC_PASSION_WEEK_v1"',
            '"DAN2_CLUSTER_v1"',
            '"dropped_edges"',
        ],
        "max_bytes": 16384,
    },
    {
        "id": "mkmlife_drilldown_passion_sidecar_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_drilldown_shard/SYNOPTIC_PASSION_WEEK_v1.json",
        "markers": [
            '"schema": "magic_orb_drilldown_shard_v1"',
            '"sample_dropped_edges"',
            '"parallel"',
        ],
        "max_bytes": 131072,
        "optional": True,
    },
    {
        "id": "mkmlife_chronology_shard_highlight_static",
        "tier": "core",
        "url": "https://mkmlife.com/data/magic_orb_chronology_shard_highlight_v1.json",
        "markers": [
            '"schema": "magic_orb_chronology_shard_highlight_v1"',
            '"shard_node_ids"',
            '"display_node_ids"',
        ],
        "max_bytes": 65536,
    },
    {
        "id": "mkmlife_shard_explorer_policy_static",
        "tier": "core",
        "url": "https://mkmlife.com/data/magic_orb_shard_explorer_policy_v1.json",
        "markers": [
            '"schema": "magic_orb_shard_explorer_policy_v1"',
            '"explorer_eligible"',
            '"canvas_size_px"',
        ],
        "max_bytes": 16384,
    },
    {
        "id": "mkmlife_graph_bloom_poc_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_graph_bloom_poc_v1.json",
        "markers": [
            '"schema": "magic_orb_graph_bloom_v1"',
            '"parallel"',
            '"integrity_tier"',
        ],
        "max_bytes": 98304,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_api_get",
        "tier": "core",
        "url": "https://mkmlife.com/api/v1/magic-orb/insight?query="
        + urllib.parse.quote("위기 가운데 언약의 안정과 신실"),
        "markers": ['"magic_orb_question_insight_v1"', '"graph_bloom"', '"integrity_tier"'],
        "max_bytes": 262144,
    },
    {
        "id": "mkmlife_insight_q08_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/23524432377849f7.json",
        "markers": ['"query_id": "q08"', '"schema": "magic_orb_graph_bloom_v1"'],
        "max_bytes": 32768,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q08_api_get",
        "tier": "extended",
        "url": "https://mkmlife.com/api/v1/magic-orb/insight?query="
        + urllib.parse.quote("고난과 위로가 함께 나타나는 성경적 패턴은 무엇인가?"),
        "markers": ['"query_id": "q08"', '"graph_bloom"'],
        "max_bytes": 32768,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q01_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/ac97b7efd98bb326.json",
        "markers": ['"query_id": "q01"', '"schema": "magic_orb_graph_bloom_v1"'],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q07_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/ac532b47d8664c36.json",
        "markers": ['"query_id": "q07"', "Jer.31.33"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q02_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/e8ac9e70c843d1e6.json",
        "markers": [
            '"query_id": "q02"',
            "logos_concept_bridge_gold_q02_judgment_warning_collapse",
        ],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q05_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/5d940bba424da73b.json",
        "markers": [
            '"query_id": "q05"',
            "logos_concept_bridge_gold_q12_risk_excess_cycle_unwind",
        ],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q03_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/e6e606a225eceaf1.json",
        "markers": [
            '"query_id": "q03"',
            "logos_concept_bridge_gold_q04_judgment_covenant_remnant",
        ],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q04_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_insight_by_query/482fb24be6f1ec09.json",
        "markers": [
            '"query_id": "q04"',
            "logos_concept_bridge_gold_q04_judgment_covenant_remnant",
        ],
        "max_bytes": 32768,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_q04_api_get",
        "tier": "extended",
        "url": "https://mkmlife.com/api/v1/magic-orb/insight?query="
        + urllib.parse.quote(
            "심판의 경고 이후에도 언약의 잔류가 남는다는 성경적 논증은, "
            "어떤 구절·경로(chain)로 연결되는가?"
        ),
        "markers": ['"query_id": "q04"', '"graph_bloom"'],
        "max_bytes": 32768,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_theatre_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_question_insight_v1_latest.json",
        "markers": [
            '"reasoning_theatre_v1"',
            '"schema": "magic_orb_reasoning_theatre_v1"',
        ],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_api_theatre",
        "tier": "extended",
        "url": "https://mkmlife.com/api/v1/magic-orb/insight?query="
        + urllib.parse.quote("위기 가운데 언약의 안정과 신실"),
        "markers": ['"reasoning_theatre_v1"', '"magic_orb_reasoning_theatre_v1"'],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_four_slot_static",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_question_insight_v1_latest.json",
        "markers": [
            '"four_slot_response_v1"',
            '"interpretive_trajectory_v1"',
            '"pipeline_waveform_v1"',
            '"send_gate": "HOLD"',
        ],
        "max_bytes": 98304,
        "optional": True,
    },
    {
        "id": "mkmlife_insight_job_static",
        "tier": "job_four_slot",
        "url": f"https://mkmlife.com/data/magic_orb_insight_by_query/{JOB_HASH}.json",
        "markers": [
            '"query_id": "job_suffering_reason"',
            '"four_slot_response_v1"',
            '"send_gate": "HOLD"',
        ],
        "max_bytes": 98304,
    },
    {
        "id": "mkmlife_insight_job_api_get",
        "tier": "job_four_slot",
        "url": "https://mkmlife.com/api/v1/magic-orb/insight?query=" + urllib.parse.quote(JOB_QUERY),
        "markers": [
            '"panorama_summary_v1"',
            '"four_slot_response_v1"',
        ],
        "markers_any": [
            ['"schema": "magic_orb_panorama_summary_v1"', '"four_slot_response_v1"'],
        ],
        "max_bytes": 98304,
    },
    {
        "id": "mkmlife_reasoning_theatre_static_json",
        "tier": "extended",
        "url": "https://mkmlife.com/data/magic_orb_reasoning_theatre_v1_latest.json",
        "markers": ['"schema": "magic_orb_reasoning_theatre_v1"', '"steps"'],
        "max_bytes": 16384,
        "optional": True,
    },
]

PROFILE_TIERS = {
    "core": {"core"},
    "extended": {"core", "extended"},
    "full": {"core", "extended", "job_four_slot"},
    "job_four_slot": {"job_four_slot"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, timeout: int = 25, max_bytes: int = 4096) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-probe-magic-orb/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes).decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)


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
        status, body, err = _fetch(row["url"], max_bytes=max_b)
        missing = [m for m in row.get("markers") or [] if m not in body]
        for group in row.get("markers_any") or []:
            if not any(marker in body for marker in group):
                missing.append("|".join(group))
        forbidden = [m for m in row.get("forbid_markers") or [] if m in body]
        expect_status = row.get("expect_status")
        if expect_status is not None:
            core_ok = status == expect_status
            markers_ok = True
        else:
            core_ok = status is not None and 200 <= status < 400 and err is None
            markers_ok = not missing and not forbidden
        optional = bool(row.get("optional"))
        ok = core_ok and (markers_ok or optional)
        results.append(
            {
                "id": row["id"],
                "tier": row.get("tier"),
                "url": row["url"],
                "status": status,
                "markers": row.get("markers") or [],
                "missing_markers": missing,
                "forbidden_markers": forbidden,
                "optional": optional,
                "ok": ok,
                "error": err,
            }
        )

    core_all_ok = _tier_ok(results, "core") if "core" in tiers else True
    extended_all_ok = _tier_ok(results, "extended") if "extended" in tiers else True
    job_four_slot_ok = _tier_ok(results, "job_four_slot") if "job_four_slot" in tiers else True
    legacy_all_ok = all(r["ok"] for r in results)

    if profile == "core":
        gate_ok = core_all_ok
    elif profile == "extended":
        gate_ok = core_all_ok and extended_all_ok
    elif profile == "job_four_slot":
        gate_ok = job_four_slot_ok
    else:
        gate_ok = core_all_ok

    schema = "magic_orb_job_four_slot_live_probe_v1" if profile == "job_four_slot" else "magic_orb_live_probe_v1"
    doc = {
        "schema": schema,
        "profile": profile,
        "checked_at_utc": _now(),
        "verdict_ko": "probe OK" if gate_ok else "probe 실패",
        "core_all_ok": core_all_ok,
        "extended_all_ok": extended_all_ok,
        "job_four_slot_ok": job_four_slot_ok,
        "legacy_all_ok": legacy_all_ok,
        "all_ok": gate_ok,
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if profile != "job_four_slot":
        history_row = {
            "checked_at_utc": doc["checked_at_utc"],
            "profile": profile,
            "all_ok": gate_ok,
            "core_all_ok": core_all_ok,
            "job_four_slot_ok": job_four_slot_ok,
            "legacy_all_ok": legacy_all_ok,
            "verdict_ko": doc["verdict_ko"],
            "results": [
                {
                    "id": r["id"],
                    "tier": r.get("tier"),
                    "status": r["status"],
                    "ok": r["ok"],
                    "optional": r.get("optional", False),
                }
                for r in results
            ],
        }
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(history_row, ensure_ascii=False) + "\n")

    return doc, 0 if gate_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILE_TIERS),
        default="full",
        help="Which probe tiers to run and gate on (default: full gates on core only).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc, code = run_probe(profile=args.profile, out_path=args.out)
    rel = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"Wrote {rel} profile={args.profile} all_ok={doc['all_ok']}")
    if args.profile != "job_four_slot":
        print(f"Appended {HISTORY.relative_to(ROOT)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
