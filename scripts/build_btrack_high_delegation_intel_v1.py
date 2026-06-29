#!/usr/bin/env python3
"""B-track high-delegation intel bundle — public showroom + atproto dry-run + local SSOT slices.

[HYPO] / research_only — Track A·live·Final Action auto-merge forbidden.
Completion: exit 0 + reports/btrack_high_delegation_intel_v1_latest.json + reproducible_command.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "btrack_high_delegation_intel_v1_latest.json"
SHOWROOM_URL = "https://jemaai.cloud/showroom_macro_horizon_2030_slice_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, tail[-2000:]


def _fetch_json_url(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-BTrack-Intel/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _github_public_releases(owner: str, repo: str, limit: int = 3) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={limit}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MKM-BTrack-Intel/1", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            items = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http_status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    if not isinstance(items, list):
        return {"ok": False, "error": "unexpected response shape"}
    slim = [
        {
            "tag_name": x.get("tag_name"),
            "name": x.get("name"),
            "published_at": x.get("published_at"),
            "html_url": x.get("html_url"),
        }
        for x in items[:limit]
        if isinstance(x, dict)
    ]
    return {"ok": True, "owner": owner, "repo": repo, "releases": slim}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--showroom-url", default=SHOWROOM_URL)
    ap.add_argument("--skip-atproto", action="store_true")
    ap.add_argument("--live-atproto", action="store_true", help="Run test_atproto_bluesky_bridge.py (requires BSKY_* env)")
    ap.add_argument("--atproto-limit", type=int, default=50, help="Live atproto sample cap (default 50)")
    ap.add_argument("--skip-github", action="store_true")
    ap.add_argument("--github-owner", default="")
    ap.add_argument("--github-repo", default="")
    ap.add_argument("--max-age-hours", type=int, default=48)
    ap.add_argument(
        "--include-swarm-downstream",
        action="store_true",
        help="Append swarm tier_a + stage1 accumulation from reports/*_latest.json",
    )
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    # 1) jemaai showroom macro JSON (public)
    showroom: dict[str, Any] = {"url": args.showroom_url}
    try:
        body = _fetch_json_url(args.showroom_url)
        showroom.update(
            {
                "ok": True,
                "keys": sorted(body.keys())[:24],
                "boundary_ack": body.get("boundary_ack"),
                "generated_at": body.get("generated_at_utc") or body.get("ts_utc"),
                "sample_size_bytes": len(json.dumps(body, ensure_ascii=False)),
            }
        )
        steps["jemaai_showroom_macro"] = {"exit_code": 0, "ok": True}
    except Exception as exc:
        showroom.update({"ok": False, "error": str(exc)})
        steps["jemaai_showroom_macro"] = {"exit_code": 1, "ok": False, "error": str(exc)}
        ok = False

    # 2) Bluesky / ATProto B-track (repo script only; B-track isolated path)
    if args.skip_atproto:
        steps["atproto_bluesky"] = {"exit_code": 0, "ok": True, "note": "skipped"}
        atproto = {"skipped": True}
    elif args.live_atproto:
        code, tail = _run(
            [
                PY,
                str(ROOT / "scripts/test_atproto_bluesky_bridge.py"),
                "--limit",
                str(max(1, min(args.atproto_limit, 200))),
            ]
        )
        out_glob = list(
            (ROOT / "projects/bitcoin-trading/memory/v2/btrack/raw_feeds/atproto").glob("*_atproto_sentiment_raw.jsonl*")
        )
        latest_out = max(out_glob, key=lambda p: p.stat().st_mtime) if out_glob else None
        steps["atproto_bluesky"] = {"exit_code": code, "ok": code == 0, "mode": "live", "tail": tail[-400:]}
        atproto = {
            "mode": "live",
            "limit": args.atproto_limit,
            "ok": code == 0,
            "latest_artifact": str(latest_out.relative_to(ROOT)).replace("\\", "/") if latest_out else None,
            "boundary_ack": "B-track raw_feeds only; Track A auto-merge forbidden",
        }
        if code != 0:
            ok = False
    else:
        code, tail = _run([PY, str(ROOT / "scripts/test_atproto_bluesky_bridge.py"), "--dry-run"])
        steps["atproto_bluesky"] = {"exit_code": code, "ok": code == 0, "mode": "dry_run", "tail": tail[-400:]}
        atproto = {"mode": "dry_run", "dry_run_ok": code == 0, "script": "scripts/test_atproto_bluesky_bridge.py --dry-run"}
        if code != 0:
            ok = False

    # 3) three-lens external intel snapshot (local chain)
    tl_out = ROOT / "docs/final/artifacts/three_lens_external_intel_snapshot_latest.json"
    code, _ = _run(
        [
            PY,
            str(ROOT / "scripts/build_three_lens_external_intel_snapshot_v1.py"),
            "--max-age-hours",
            str(args.max_age_hours),
            "--output-json",
            str(tl_out),
        ]
    )
    three_lens = _safe_read_json(tl_out)
    steps["three_lens_external_snapshot"] = {"exit_code": code, "ok": code == 0, "artifact": str(tl_out.relative_to(ROOT)).replace("\\", "/")}
    if code != 0:
        ok = False

    # 4) Track C ops dashboard slice (local SSOT, no scrape)
    dash = _safe_read_json(ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json")
    trackc = {
        "present": bool(dash),
        "generated_at_utc": dash.get("generated_at_utc"),
        "send_gate": ((dash.get("trackc") or {}).get("send_gate") if isinstance(dash.get("trackc"), dict) else None),
        "boundary_ack": "[HYPO] observation only — not Track A trigger",
    }
    steps["trackc_dashboard_slice"] = {"exit_code": 0, "ok": bool(dash)}

    # 5) Optional public GitHub releases (whitelist owner/repo)
    if args.skip_github or not (args.github_owner and args.github_repo):
        github = {"skipped": True, "note": "pass --github-owner/--github-repo for public API whitelist"}
        steps["github_public_releases"] = {"exit_code": 0, "ok": True, "note": "skipped_no_whitelist"}
    else:
        github = _github_public_releases(args.github_owner, args.github_repo)
        steps["github_public_releases"] = {"exit_code": 0 if github.get("ok") else 1, "ok": bool(github.get("ok"))}
        if not github.get("ok"):
            ok = False

    if args.include_swarm_downstream:
        swarm_downstream = {
            "tier_a_prereqs": _safe_read_json(ROOT / "reports/btrack_swarm_tier_a_prereqs_v1_latest.json"),
            "stage1_accumulation": _safe_read_json(
                ROOT / "reports/btrack_swarm_sasang_stage1_accumulation_v1_latest.json"
            ),
            "stage1_hold": _safe_read_json(ROOT / "reports/btrack_swarm_sasang_stage1_hold_v1_latest.json"),
            "atproto_backfill": _safe_read_json(ROOT / "reports/btrack_atproto_backfill_v1_latest.json"),
            "swarm_jsonl": "data/btrack/swarm_sentiment_real_pit_v1.jsonl",
            "boundary_ack": "[HYPO] Swarm×Sasang stage1 — tier_a 30 rows gate; Track A merge forbidden",
        }
        steps["swarm_downstream_snapshot"] = {
            "exit_code": 0,
            "ok": True,
            "tier_a_ready": bool(swarm_downstream.get("tier_a_prereqs", {}).get("tier_a_ready")),
        }
    else:
        swarm_downstream = None

    repro = "py scripts/build_btrack_high_delegation_intel_v1.py"
    if args.live_atproto:
        repro += f" --live-atproto --atproto-limit {args.atproto_limit}"
    if args.github_owner and args.github_repo:
        repro += f" --github-owner {args.github_owner} --github-repo {args.github_repo}"
    if args.include_swarm_downstream:
        repro += " --include-swarm-downstream"

    payload: dict[str, Any] = {
        "schema": "btrack_high_delegation_intel_v1",
        "generated_at_utc": _utc(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
        "final_action": "HOLD_EXTERNAL_INTEL_REGISTER",
        "final_action_detail_ko": "수집·정규화·격벽 태그만; 본선·MS·Final Call 자동 합선 금지",
        "field": "multi_domain_btrack_intel",
        "lens": {
            "sasang": "외부·소셜·쇼룸 신호 강도 관측 [HYPO]",
            "myeongni": "중기 매크로·뉴스 방향 보조 [HYPO]",
            "logos": "거시 게이트 — 본 산출은 [NON_GATING] 참고",
        },
        "conflict": "freshness·출처 화이트리스트 밖 데이터는 미포함",
        "sources": {
            "jemaai_showroom_macro": showroom,
            "atproto_bluesky": atproto,
            "three_lens_external": three_lens,
            "trackc_dashboard": trackc,
            "github_public": github,
            **({"swarm_downstream": swarm_downstream} if swarm_downstream else {}),
        },
        "steps": steps,
        "ok": ok,
        "reproducible_command": repro,
        "a2a_coordinate_pointers": {
            "resume_pack": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
            "ops_memory_index": "storage/meta/mkm_ops_memory_index_v1.json",
            "a2a_lane_index": "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json",
            "trinity_index": "docs/final/MKM_TRINITY_INDEX_V1.json",
            "note": "domain 'common sense' = pinned coords + lane packs, not encyclopedia in chat",
        },
    }

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(out_path), "steps_ok": sum(1 for s in steps.values() if s.get("ok"))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
