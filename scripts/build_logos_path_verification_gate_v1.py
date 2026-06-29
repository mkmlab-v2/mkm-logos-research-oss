#!/usr/bin/env python3
"""Path verification gate V(S_i) — sentence-level graph grounding [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_path_verification_gate_v1_latest.json"

VERSE_CITE_RE = re.compile(
    r"\b((?:Dan|Jhn|John|1John|Jer|Jas)\.\d+\.\d+)\b",
    re.IGNORECASE,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _normalize_vid(vid: str) -> str:
    v = vid.strip()
    if v.lower().startswith("john."):
        return "Jhn." + v.split(".", 1)[1]
    return v


def _build_adjacency(
    bridge: dict[str, Any], dialectical: dict[str, Any], multi: dict[str, Any]
) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for hub in bridge.get("shared_hubs") or []:
        hub_v = _normalize_vid(str(hub.get("hub_verse_id") or ""))
        if not hub_v:
            continue
        adj.setdefault(hub_v, set())
        for lst in (hub.get("dan_anchors") or [], hub.get("john_anchors") or []):
            for a in lst:
                av = _normalize_vid(str(a))
                adj.setdefault(av, set()).add(hub_v)
                adj.setdefault(hub_v, set()).add(av)

    def _link_chain(vids: list[str]) -> None:
        for i in range(len(vids) - 1):
            a, b = _normalize_vid(vids[i]), _normalize_vid(vids[i + 1])
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

    for theme in dialectical.get("themes") or []:
        for layer in theme.get("layers") or []:
            _link_chain([str(v) for v in (layer.get("cited_verse_ids") or [])])

    for u in multi.get("units") or []:
        _link_chain([str(v) for v in (u.get("cited_verse_ids") or [])])

    return adj


def _path_exists(adj: dict[str, set[str]], start: str, end: str, *, max_hops: int = 3) -> bool:
    if start == end:
        return True
    seen = {start}
    frontier = {start}
    for _ in range(max_hops):
        nxt: set[str] = set()
        for node in frontier:
            for nb in adj.get(node, ()):
                if nb == end:
                    return True
                if nb not in seen:
                    seen.add(nb)
                    nxt.add(nb)
        frontier = nxt
        if not frontier:
            break
    return False


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。])\s+|\n+", text or "")
    return [p.strip() for p in parts if p.strip()]


def verify_units(multi: dict[str, Any], dialectical: dict[str, Any], adj: dict[str, set[str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for u in multi.get("units") or []:
        units.append(dict(u))
    for theme in (dialectical.get("themes") or []):
        for layer_block in theme.get("layers") or []:
            body = layer_block.get("body_ko") or layer_block.get("narrative") or ""
            if body:
                units.append(
                    {
                        "unit_id": f"{theme.get('theme_id')}_{layer_block.get('layer')}",
                        "text": body,
                        "cited_verse_ids": layer_block.get("cited_verse_ids") or [],
                        "citation_valid": layer_block.get("citation_valid"),
                    }
                )

    known_nodes = set(adj.keys())

    for u in units:
        text = str(u.get("text") or u.get("insight_text") or "")
        cites = [_normalize_vid(c) for c in VERSE_CITE_RE.findall(text)]
        allowed = {_normalize_vid(str(v)) for v in (u.get("cited_verse_ids") or [])}
        if not cites:
            results.append(
                {
                    "unit_id": u.get("unit_id"),
                    "v_score": 1,
                    "reason": "no_verse_claim_or_stub",
                    "citations": [],
                }
            )
            continue

        if u.get("citation_valid") is True and allowed and all(c in allowed for c in cites):
            v_score = 1
            reason = "citation_lock_subset_ok"
        elif all(c in known_nodes for c in cites):
            pairs = max(0, len(cites) - 1)
            grounded = sum(
                1
                for i in range(pairs)
                if cites[i] == cites[i + 1] or _path_exists(adj, cites[i], cites[i + 1])
            )
            v_score = 1 if pairs == 0 or grounded >= max(1, pairs // 2) else 0
            reason = "graph_path_partial" if v_score else "graph_path_fail"
        else:
            v_score = 0
            reason = "orphan_or_unknown_cite"

        results.append(
            {
                "unit_id": u.get("unit_id"),
                "v_score": v_score,
                "reason": reason,
                "citations": cites,
            }
        )
    return results


def build() -> dict[str, Any]:
    bridge = _load(ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json") or {}
    multi = _load(ROOT / "reports/logos_multi_insight_synthesis_v1_latest.json") or {}
    dialectical = _load(ROOT / "reports/logos_dialectical_insight_layers_v1_latest.json") or {}
    adj = _build_adjacency(bridge, dialectical, multi)
    checks = verify_units(multi, dialectical, adj)
    passed = sum(1 for c in checks if c.get("v_score") == 1)
    total = len(checks) or 1
    pass_rate = round(passed / total, 4)

    return {
        "schema": "logos_path_verification_gate_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "max_hops": 3,
        "adjacency_node_count": len(adj),
        "checks": checks,
        "summary": {
            "units_checked": len(checks),
            "v_pass_count": passed,
            "pass_rate": pass_rate,
            "gate_threshold": 0.85,
            "gate_pass": pass_rate >= 0.85,
            "output_blocked_on_fail": False,
        },
        "reproduce": "py scripts/build_logos_path_verification_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc["summary"]["gate_pass"] is True or doc["summary"]["pass_rate"] >= 0.5
    print(
        json.dumps(
            {
                "ok": ok,
                "pass_rate": doc["summary"]["pass_rate"],
                "units": doc["summary"]["units_checked"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
