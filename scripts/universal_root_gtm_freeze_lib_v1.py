#!/usr/bin/env python3

"""Shared UR GTM FREEZE evaluation [HYPO · send_gate HOLD]."""



from __future__ import annotations



import json

from datetime import datetime, timezone

from pathlib import Path

from typing import Any



ROOT = Path(__file__).resolve().parents[1]

GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"

POLL = ROOT / "reports/universal_root_community_poll_v1_latest.json"

FREEZE_SSOT = ROOT / "docs/final/artifacts/universal_root_gtm_freeze_v1_latest.json"





def _utc() -> str:

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")





def _read_json(path: Path) -> dict[str, Any]:

    if not path.is_file():

        return {}

    return json.loads(path.read_text(encoding="utf-8-sig"))





def external_repro_count(gtm: dict[str, Any] | None = None, poll: dict[str, Any] | None = None) -> int:

    gtm = gtm if gtm is not None else _read_json(GTM)

    poll = poll if poll is not None else _read_json(POLL)

    gh = (gtm.get("channels") or {}).get("github_discussions") or {}

    n = int(gh.get("external_repro_reports") or 0)

    disc = (poll.get("discussion") or {}) if poll else {}

    if disc:

        n = max(n, int(disc.get("external_repro_like_count") or 0))

        if n == 0:

            n = max(n, int(disc.get("external_comment_count") or 0))

    return n





def freeze_active(gtm: dict[str, Any] | None = None) -> bool:

    gtm = gtm if gtm is not None else _read_json(GTM)

    block = gtm.get("gtm_freeze") or {}

    if block.get("active") is True:

        return True

    ssot = _read_json(FREEZE_SSOT)

    return bool(ssot.get("public_gtm_allowed") is False)





def evaluate_gtm_freeze(

    *,

    gtm: dict[str, Any] | None = None,

    poll: dict[str, Any] | None = None,

    action: str = "read_only",

    commander_override: bool = False,

    skip_integrity: bool = False,

) -> dict[str, Any]:

    from scripts.universal_root_gtm_integrity_lib_v1 import evaluate_phase1a_integrity  # noqa: WPS433
    from scripts.universal_root_public_push_gate_lib_v1 import evaluate_named_public_bench  # noqa: WPS433



    gtm = gtm if gtm is not None else _read_json(GTM)

    poll = poll if poll is not None else _read_json(POLL)

    ssot = _read_json(FREEZE_SSOT)

    block = gtm.get("gtm_freeze") or {}

    active = freeze_active(gtm)

    ext = external_repro_count(gtm, poll)

    gh = (gtm.get("channels") or {}).get("github_discussions") or {}

    bump_policy = str(gh.get("bump_policy") or block.get("maintainer_bump_policy") or "hold_until_external_repro")

    min_repro = int(ssot.get("rules", {}).get("min_external_repro_for_gtm", 1))



    integrity = {"integrity_ok": True, "violations": [], "skipped": True} if skip_integrity else evaluate_phase1a_integrity()

    integrity_ok = bool(integrity.get("integrity_ok"))

    named_bench = evaluate_named_public_bench()

    named_bench_ok = bool(named_bench.get("named_public_bench_ok"))



    hold_reasons: list[str] = []

    if active and ext < min_repro:

        hold_reasons.append("external_repro_below_min")

    if active and not integrity_ok:

        hold_reasons.append("phase1a_integrity_failed")

    if active and not named_bench_ok:

        hold_reasons.append("named_public_bench_missing")



    public_gtm_allowed = True

    if active:

        public_gtm_allowed = ext >= min_repro and integrity_ok and named_bench_ok



    violations: list[str] = []

    if active and ext < min_repro and action in {

        "maintainer_bump",

        "discussions_live_post",

        "x_live_post",

        "reddit_live_post",

    }:

        if not commander_override:

            violations.append(f"gtm_freeze_blocks_{action}")

    if active and not integrity_ok and action in {

        "maintainer_bump",

        "discussions_live_post",

        "x_live_post",

        "reddit_live_post",

    }:

        if not commander_override:

            violations.append("phase1a_integrity_blocks_live_gtm")

    if active and not named_bench_ok and action in {

        "maintainer_bump",

        "discussions_live_post",

        "x_live_post",

        "reddit_live_post",

    }:

        if not commander_override:

            violations.append("named_public_bench_blocks_live_gtm")

    ur_w1 = (gtm.get("milestones") or {}).get("UR-W1") or {}

    if active and ext < min_repro and ur_w1.get("status") == "partial_complete":

        violations.append("ur_w1_partial_complete_while_frozen")



    action_ok = not violations

    return {

        "schema": "universal_root_gtm_freeze_eval_v1",

        "version": "1.1.0",

        "evaluated_at_utc": _utc(),

        "active": active,

        "integrity_ok": integrity_ok,

        "integrity": integrity,

        "named_public_bench_ok": named_bench_ok,

        "named_public_bench": named_bench,

        "public_gtm_allowed": public_gtm_allowed,

        "external_repro_count": ext,

        "min_external_repro_for_gtm": min_repro,

        "hold_reasons": hold_reasons,

        "bump_policy": bump_policy,

        "action": action,

        "commander_override": commander_override,

        "violations": violations,

        "ok": action_ok,

        "freeze_ssot": str(FREEZE_SSOT.relative_to(ROOT)).replace("\\", "/"),

    }


