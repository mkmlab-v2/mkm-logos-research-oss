#!/usr/bin/env python3
"""MKM hybrid LLM data router — deterministic DC × MR lookup (policy v1).

Loads docs/final/artifacts/mkm_hybrid_llm_data_router_v1_latest.json.
No LLM calls. research_only · B-track · SEND_GATE HOLD.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs/final/artifacts/mkm_hybrid_llm_data_router_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/mkm_hybrid_llm_data_route_resolve_v1_latest.json"

SCHEMA = "mkm_hybrid_llm_data_route_resolve_v1"
RESEARCH_ONLY = True

DATA_CLASSES = frozenset({"DC-PUBLIC", "DC-INTERNAL", "DC-RESTRICTED", "DC-SOVEREIGN"})
MODEL_ROUTES = frozenset(
    {"MR-LOCAL-SLM", "MR-LOCAL-LORA", "MR-SAAS-FRONTIER", "MR-HUMAN"}
)
DEFAULT_ROUTE_BY_CLASS: dict[str, str] = {
    "DC-PUBLIC": "MR-LOCAL-SLM",
    "DC-INTERNAL": "MR-LOCAL-SLM",
    "DC-RESTRICTED": "MR-LOCAL-SLM",
    "DC-SOVEREIGN": "MR-LOCAL-SLM",
}

PATH_HINT_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\.env$|dpapi|api[_-]?key|secret"), "DC-SOVEREIGN"),
    (re.compile(r"(?i)original_language_master_atoms|unmasked|phi"), "DC-SOVEREIGN"),
    (
        re.compile(r"(?i)stateless_poc_|must_keep|paste_ready|intake|tenant_"),
        "DC-RESTRICTED",
    ),
    (re.compile(r"(?i)reports/demo/|showroom|static_hub"), "DC-PUBLIC"),
    (re.compile(r"(?i)reports/|docs/final/artifacts/"), "DC-INTERNAL"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing policy: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "mkm_hybrid_llm_data_router_v1":
        raise ValueError(f"unexpected policy schema: {data.get('schema')}")
    return data


def _matrix_index(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in policy.get("routing_matrix") or []:
        dc = str(row.get("data_class") or "")
        if dc:
            out[dc] = row
    return out


def infer_data_class(path_hint: str, *, ambiguous_default: str = "DC-RESTRICTED") -> str:
    hint = (path_hint or "").replace("\\", "/").strip()
    if not hint:
        return ambiguous_default
    for pattern, dc in PATH_HINT_RULES:
        if pattern.search(hint):
            return dc
    return ambiguous_default


def allowed_routes(data_class: str, policy: dict[str, Any] | None = None) -> list[str]:
    if data_class not in DATA_CLASSES:
        raise ValueError(f"unknown data_class: {data_class}")
    pol = policy or load_policy()
    row = _matrix_index(pol).get(data_class)
    if not row:
        raise ValueError(f"no routing_matrix row for {data_class}")
    routes = [str(r) for r in row.get("allowed_routes") or []]
    if not routes:
        raise ValueError(f"empty allowed_routes for {data_class}")
    return routes


def is_route_allowed(data_class: str, route: str, policy: dict[str, Any] | None = None) -> bool:
    if route not in MODEL_ROUTES:
        return False
    return route in allowed_routes(data_class, policy)


def resolve_route(
    data_class: str,
    *,
    requested_route: str | None = None,
    path_hint: str = "",
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pol = policy or load_policy()
    dc = data_class
    if not dc and path_hint:
        dc = infer_data_class(path_hint)
    if dc not in DATA_CLASSES:
        raise ValueError(f"unknown data_class: {dc}")

    allowed = allowed_routes(dc, pol)
    row = _matrix_index(pol)[dc]
    forbidden = [str(x) for x in row.get("forbidden") or []]

    if requested_route:
        route = requested_route
        if not is_route_allowed(dc, route, pol):
            raise ValueError(f"route {route} not allowed for {dc}; allowed={allowed}")
    else:
        route = DEFAULT_ROUTE_BY_CLASS.get(dc, allowed[0])
        if route not in allowed:
            route = allowed[0]

    return {
        "data_class": dc,
        "route": route,
        "allowed_routes": allowed,
        "forbidden": forbidden,
        "path_hint": path_hint or None,
        "research_only": RESEARCH_ONLY,
        "send_gate": pol.get("send_gate", "HOLD"),
        "policy_ref": str(pol.get("human_doc") or DEFAULT_POLICY.as_posix()),
    }


def build_report(
    *,
    data_class: str = "",
    requested_route: str | None = None,
    path_hint: str = "",
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    resolution = resolve_route(
        data_class or infer_data_class(path_hint),
        requested_route=requested_route,
        path_hint=path_hint,
        policy=policy,
    )
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "ok": True,
        "research_only": RESEARCH_ONLY,
        "policy_path": policy_path.as_posix(),
        "resolution": resolution,
        "reproduce": (
            "py scripts/resolve_mkm_hybrid_llm_data_route_v1.py "
            f"--data-class {resolution['data_class']}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-class", default="", help="DC-PUBLIC | DC-INTERNAL | ...")
    ap.add_argument("--route", default="", help="Requested MR-* route (validated)")
    ap.add_argument("--path-hint", default="", help="Infer DC when --data-class omitted")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    try:
        report = build_report(
            data_class=args.data_class.strip(),
            requested_route=args.route.strip() or None,
            path_hint=args.path_hint.strip(),
            policy_path=args.policy,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"resolve_mkm_hybrid_llm_data_route_v1=FAIL reason={exc}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dc = report["resolution"]["data_class"]
    route = report["resolution"]["route"]
    print(f"resolve_mkm_hybrid_llm_data_route_v1=OK data_class={dc} route={route} out={args.out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
