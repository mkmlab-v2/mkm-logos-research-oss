#!/usr/bin/env python3
"""WTT premium CS — economy shortcap + literal fallback hybrid codec router PoC [HYPO].

Per-case routing: default economy_shortcap_30_020; on jaccard fail retry literal.
Also benchmarks turn-count and assistant-presence heuristics. research_only · SEND HOLD.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKEN_RE = re.compile(r"\S+")
DEFAULT_CORPUS = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"
DEFAULT_OUT = ROOT / "reports/wtt_cs_hybrid_codec_router_poc_v1_latest.json"
JACCARD_FLOOR = 0.73
ECONOMY_SHORT_THRESHOLD = 30
ECONOMY_SHORT_MAX_SAVING = 0.20


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _token_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in ("text", "raw_text", "content", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def turn_count(obj: dict[str, Any]) -> int:
    turns = obj.get("turns")
    if isinstance(turns, list) and turns:
        return len(turns)
    return 0


def has_assistant_turn(obj: dict[str, Any]) -> bool:
    turns = obj.get("turns")
    if not isinstance(turns, list):
        return False
    return any(isinstance(t, dict) and str(t.get("role") or "").lower() == "assistant" for t in turns)


def select_profile_turns_gte(
    obj: dict[str, Any],
    *,
    min_turns: int,
    literal_profile: str = "literal",
    default_profile: str = "economy",
) -> tuple[str, str]:
    if turn_count(obj) >= min_turns:
        return literal_profile, f"turn_count>={min_turns}"
    return default_profile, "economy_default"


def select_profile_assistant_literal(
    obj: dict[str, Any],
    *,
    literal_profile: str = "literal",
    default_profile: str = "economy",
) -> tuple[str, str]:
    if has_assistant_turn(obj):
        return literal_profile, "has_assistant_turn"
    return default_profile, "economy_default"


def _compress_profile_args(profile: str) -> dict[str, Any]:
    body: dict[str, Any] = {"compression_profile": profile}
    if profile in ("economy", "fidelity"):
        body["short_context_token_threshold"] = ECONOMY_SHORT_THRESHOLD
        body["short_context_max_saving_rate"] = ECONOMY_SHORT_MAX_SAVING
    return body


def _evaluate_row(
    client: Any,
    *,
    text: str,
    row_id: str,
    profile: str,
    overlay_terms: list[str],
    forced_shard_id: str | None,
    jaccard_floor: float,
) -> dict[str, Any]:
    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY
    from scripts.report_multilens_performance_eval import _jaccard

    compress_body: dict[str, Any] = {
        "text": text,
        "loss_profile": "semantic_general",
        "client_request_id": f"hybrid-poc-{row_id}-{profile}",
        "stateless_packet": True,
        **_compress_profile_args(profile),
    }
    if forced_shard_id:
        compress_body["forced_shard_id"] = forced_shard_id
    if overlay_terms:
        compress_body["must_keep_overlay_terms"] = overlay_terms

    cr = client.post("/v2/compress", json=compress_body)
    if cr.status_code != 200:
        return {"ok": False, "error": cr.text[:200], "compression_profile": profile}

    cr_body = cr.json()
    pkt = cr_body.get("compression_packet") or {}
    stub = (pkt.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
    if "reconstructed_text" in stub:
        return {
            "ok": False,
            "error": "stateless_packet_leaked_reconstructed_text",
            "compression_profile": profile,
        }

    er = client.post("/v2/expand", json={"compression_packet": pkt, "decode_mode": "codebook_only"})
    if er.status_code != 200:
        return {"ok": False, "error": er.text[:200], "compression_profile": profile}

    expanded = er.json().get("text") or ""
    tin = _token_proxy(text)
    tout = _token_proxy(str(pkt.get("compressed_text") or ""))
    saving = max(0.0, 1.0 - (tout / tin)) if tin > 0 else 0.0
    jac = float(_jaccard(text, expanded))
    ok = jac >= jaccard_floor
    return {
        "ok": ok,
        "exact_restore": expanded == text,
        "token_in_proxy": tin,
        "token_out_proxy": tout,
        "token_saving_rate_proxy": round(saving, 6),
        "jaccard_proxy": round(jac, 6),
        "reassembly": (er.json().get("integrity_flags") or {}).get("reassembly"),
        "compression_profile": profile,
    }


def run_economy_fallback_literal(
    client: Any,
    *,
    obj: dict[str, Any],
    text: str,
    row_id: str,
    overlay_terms: list[str],
    forced_shard_id: str | None,
    jaccard_floor: float,
) -> dict[str, Any]:
    primary = _evaluate_row(
        client,
        text=text,
        row_id=row_id,
        profile="economy",
        overlay_terms=overlay_terms,
        forced_shard_id=forced_shard_id,
        jaccard_floor=jaccard_floor,
    )
    if primary.get("ok"):
        return {
            **primary,
            "route_policy": "economy_then_literal_fallback",
            "route_reason": "economy_pass",
            "profiles_tried": ["economy"],
            "fallback_used": False,
        }

    fallback = _evaluate_row(
        client,
        text=text,
        row_id=row_id,
        profile="literal",
        overlay_terms=overlay_terms,
        forced_shard_id=forced_shard_id,
        jaccard_floor=jaccard_floor,
    )
    chosen = fallback if fallback.get("ok") or not primary.get("ok") else primary
    return {
        **chosen,
        "route_policy": "economy_then_literal_fallback",
        "route_reason": "literal_fallback_after_economy_fail",
        "profiles_tried": ["economy", "literal"],
        "fallback_used": True,
        "economy_attempt": {
            "ok": primary.get("ok"),
            "jaccard_proxy": primary.get("jaccard_proxy"),
            "token_saving_rate_proxy": primary.get("token_saving_rate_proxy"),
        },
    }


def run_single_profile(
    client: Any,
    *,
    obj: dict[str, Any],
    text: str,
    row_id: str,
    profile: str,
    overlay_terms: list[str],
    forced_shard_id: str | None,
    jaccard_floor: float,
    route_policy: str,
    route_reason: str,
) -> dict[str, Any]:
    result = _evaluate_row(
        client,
        text=text,
        row_id=row_id,
        profile=profile,
        overlay_terms=overlay_terms,
        forced_shard_id=forced_shard_id,
        jaccard_floor=jaccard_floor,
    )
    return {
        **result,
        "route_policy": route_policy,
        "route_reason": route_reason,
        "profiles_tried": [profile],
        "fallback_used": False,
        "turn_count": turn_count(obj),
        "has_assistant_turn": has_assistant_turn(obj),
    }


PolicyRunner = Callable[..., dict[str, Any]]


def _build_policies() -> list[dict[str, Any]]:
    return [
        {
            "policy_id": "economy_shortcap_30_020_baseline",
            "description": "Fixed economy shortcap (prior 28/30 baseline).",
            "runner": "single",
            "profile": "economy",
        },
        {
            "policy_id": "literal_baseline",
            "description": "Fixed literal (prior 28/30 alternate fail set).",
            "runner": "single",
            "profile": "literal",
        },
        {
            "policy_id": "economy_then_literal_fallback",
            "description": "Try economy; on jaccard fail retry literal.",
            "runner": "economy_fallback",
        },
        {
            "policy_id": "route_turns_gte_3_literal",
            "description": "turns>=3 → literal else economy shortcap.",
            "runner": "turn_route",
            "min_turns": 3,
        },
        {
            "policy_id": "route_assistant_literal",
            "description": "Any assistant turn → literal else economy shortcap.",
            "runner": "assistant_route",
        },
    ]


def _run_policy(
    policy: dict[str, Any],
    client: Any,
    cases: list[dict[str, Any]],
    overlay_terms: list[str],
    forced_shard_id: str | None,
    jaccard_floor: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    runner = policy["runner"]
    for obj in cases:
        row_id = str(obj["id"])
        text = obj["text"]
        if runner == "single":
            profile = policy["profile"]
            row = run_single_profile(
                client,
                obj=obj,
                text=text,
                row_id=row_id,
                profile=profile,
                overlay_terms=overlay_terms,
                forced_shard_id=forced_shard_id,
                jaccard_floor=jaccard_floor,
                route_policy=policy["policy_id"],
                route_reason="fixed_profile",
            )
        elif runner == "economy_fallback":
            row = run_economy_fallback_literal(
                client,
                obj=obj,
                text=text,
                row_id=row_id,
                overlay_terms=overlay_terms,
                forced_shard_id=forced_shard_id,
                jaccard_floor=jaccard_floor,
            )
            row["turn_count"] = turn_count(obj)
            row["has_assistant_turn"] = has_assistant_turn(obj)
        elif runner == "turn_route":
            profile, reason = select_profile_turns_gte(obj, min_turns=int(policy["min_turns"]))
            row = run_single_profile(
                client,
                obj=obj,
                text=text,
                row_id=row_id,
                profile=profile,
                overlay_terms=overlay_terms,
                forced_shard_id=forced_shard_id,
                jaccard_floor=jaccard_floor,
                route_policy=policy["policy_id"],
                route_reason=reason,
            )
        elif runner == "assistant_route":
            profile, reason = select_profile_assistant_literal(obj)
            row = run_single_profile(
                client,
                obj=obj,
                text=text,
                row_id=row_id,
                profile=profile,
                overlay_terms=overlay_terms,
                forced_shard_id=forced_shard_id,
                jaccard_floor=jaccard_floor,
                route_policy=policy["policy_id"],
                route_reason=reason,
            )
        else:
            raise ValueError(f"unknown runner: {runner}")
        row["id"] = row_id
        rows.append(row)

    n = len(rows)
    n_ok = sum(1 for r in rows if r.get("ok"))
    fail_ids = [r["id"] for r in rows if not r.get("ok")]
    fallback_count = sum(1 for r in rows if r.get("fallback_used"))
    return {
        "policy_id": policy["policy_id"],
        "description": policy.get("description"),
        "case_count": n,
        "cases_passed": n_ok,
        "pass_rate": round(n_ok / n, 4) if n else 0.0,
        "fail_ids": fail_ids,
        "fallback_used_count": fallback_count,
        "mean_jaccard_all": round(
            sum(r.get("jaccard_proxy") or 0.0 for r in rows) / max(1, n), 6
        ),
        "mean_saving_all": round(
            sum(r.get("token_saving_rate_proxy") or 0.0 for r in rows) / max(1, n), 6
        ),
        "cases": rows,
    }


def _load_cases(path: Path, max_cases: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or len(cases) >= max_cases:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        cases.append({**obj, "text": text})
    return cases


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--jaccard-floor", type=float, default=JACCARD_FLOOR)
    ap.add_argument("--sku", default="MKM-CHAT-D1")
    args = ap.parse_args(argv)

    corpus = args.corpus_jsonl.resolve()
    if not corpus.is_file():
        print(f"error: missing corpus: {corpus}", file=sys.stderr)
        return 2

    overlay_terms: list[str] = []
    overlay_path = args.overlay_json.resolve()
    if overlay_path.is_file():
        from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms

        overlay_terms = load_overlay_terms(overlay_path)

    forced_shard_id: str | None = None
    if args.sku:
        from scripts.compression_b2b_off_the_shelf_shard_sku_v1_lib import build_sku_context

        sku_context = build_sku_context(
            workspace_root=ROOT,
            spec_path=ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json",
            external_sku=args.sku,
            shard_json_override=None,
        )
        forced_shard_id = sku_context.get("forced_shard_id") or sku_context.get("override_shard_id")

    cases = _load_cases(corpus, args.max_cases)
    if not cases:
        print("error: no cases loaded", file=sys.stderr)
        return 2

    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    policy_results = [
        _run_policy(p, client, cases, overlay_terms, forced_shard_id, args.jaccard_floor)
        for p in _build_policies()
    ]
    best = max(policy_results, key=lambda r: (r["cases_passed"], r["mean_jaccard_all"]))

    doc = {
        "schema": "wtt_cs_hybrid_codec_router_poc_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "input_jsonl": corpus.relative_to(ROOT).as_posix(),
        "jaccard_floor": args.jaccard_floor,
        "economy_shortcap": {
            "token_threshold": ECONOMY_SHORT_THRESHOLD,
            "max_saving_rate": ECONOMY_SHORT_MAX_SAVING,
        },
        "case_count": len(cases),
        "policies": policy_results,
        "best_policy_id": best["policy_id"],
        "best_cases_passed": best["cases_passed"],
        "conclusion_ko": (
            f"best={best['policy_id']} pass={best['cases_passed']}/{len(cases)}; "
            "Track A·SEND 승격 아님."
        ),
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        json.dumps(
            {
                "best_policy": best["policy_id"],
                "pass": f"{best['cases_passed']}/{len(cases)}",
                "fail_ids": best.get("fail_ids"),
            },
            ensure_ascii=False,
        )
    )
    primary = next(r for r in policy_results if r["policy_id"] == "economy_then_literal_fallback")
    return 0 if primary["cases_passed"] == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
