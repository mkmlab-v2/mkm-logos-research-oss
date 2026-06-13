#!/usr/bin/env python3
"""Tier 3 Cursor parallel-chat wire handoff pilot — L1 inject → L2 packet → peer expand.

[HYPO] / research_only / B-track. Human resume MD unchanged; peer chat uses lane-specific brief.

  py scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py --lane oracle
  py scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py --lane web_ops --append-log --strict-exit
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ltm_resume_lane_token_v1 import (  # noqa: E402
    _lane_inject_text,
    _lane_must_keep_overlay_terms,
)
from mkm_a2a_compress_pilot_lib_v1 import (  # noqa: E402
    compress_plaintext_v2,
    count_tokens,
    load_compress_skip_rules,
)
from mkm_ops_memory_index_lib_v1 import LANE_OPS_PACKS  # noqa: E402

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_pilot_v1_latest.json"
DEFAULT_BRIEF = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_v1_latest.md"
DEFAULT_PACKET = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_packet_v1_latest.json"
DEFAULT_LOG = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_log.jsonl"
DEFAULT_INDEX = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json"
DEFAULT_INDEX_MD = ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.md"
DEFAULT_LANE = "oracle"
JACCARD_ADAPT_FLOOR = 0.85
LANE_JACCARD_ADAPT_FLOOR: dict[str, float] = {"web_ops": 0.90}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{round(x * 100, 2)}%"


def _log_path_display(root: Path, log_path: Path) -> str:
    try:
        return log_path.relative_to(root).as_posix()
    except ValueError:
        return log_path.as_posix()


def lane_artifact_paths(root: Path, lane: str) -> dict[str, Path]:
    art = root / "docs/final/artifacts"
    return {
        "pilot": art / f"a2a_tier3_cursor_wire_handoff_pilot_{lane}_v1_latest.json",
        "brief": art / f"a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md",
        "packet": art / f"a2a_tier3_cursor_wire_handoff_packet_{lane}_v1_latest.json",
    }


def _expand_jaccard(client: Any, inject_text: str, compress_row: dict[str, Any]) -> tuple[bool, str, float | None]:
    from scripts.report_multilens_performance_eval import _jaccard

    packet = compress_row.get("trust_packet_for_expand") or compress_row.get("trust_packet_redacted")
    if compress_row.get("decision") != "compressed" or not isinstance(packet, dict):
        return False, "", None
    er = client.post("/v2/expand", json={"compression_packet": packet})
    if er.status_code != 200:
        return False, "", None
    expanded_text = (er.json() or {}).get("text") or ""
    return True, expanded_text, _jaccard(inject_text, expanded_text)


def _compress_profile_row(
    client: Any,
    inject_text: str,
    *,
    lane: str,
    min_tokens: int,
    routing_profile: str,
    loss_profile: str,
    must_keep_overlay_terms: list[str] | None = None,
) -> dict[str, Any]:
    return compress_plaintext_v2(
        client,
        inject_text,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        loss_profile=loss_profile,
        client_request_id=f"a2a-tier3-{lane}-{loss_profile}",
        must_keep_overlay_terms=must_keep_overlay_terms,
    )


def _adaptive_compress(
    client: Any,
    inject_text: str,
    *,
    lane: str,
    min_tokens: int,
    routing_profile: str,
    adapt_loss_profile: bool,
    must_keep_overlay_terms: list[str] | None = None,
) -> tuple[dict[str, Any], str, float | None, str]:
    primary = _compress_profile_row(
        client,
        inject_text,
        lane=lane,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        loss_profile="semantic_general",
        must_keep_overlay_terms=must_keep_overlay_terms,
    )
    expand_ok, expanded_text, jaccard = _expand_jaccard(client, inject_text, primary)
    selected = primary
    loss_profile_used = "semantic_general"
    adapt_note = "semantic_general only"
    adapt_floor = LANE_JACCARD_ADAPT_FLOOR.get(lane, JACCARD_ADAPT_FLOOR)

    if adapt_loss_profile and expand_ok and jaccard is not None and jaccard < adapt_floor:
        semantic_j = jaccard
        fallback = _compress_profile_row(
            client,
            inject_text,
            lane=lane,
            min_tokens=min_tokens,
            routing_profile=routing_profile,
            loss_profile="lossless_text",
            must_keep_overlay_terms=must_keep_overlay_terms,
        )
        fb_ok, fb_text, fb_j = _expand_jaccard(client, inject_text, fallback)
        if fb_ok and fb_j is not None and (jaccard is None or fb_j >= jaccard):
            selected = fallback
            expanded_text = fb_text
            jaccard = fb_j
            expand_ok = fb_ok
            loss_profile_used = "lossless_text"
            adapt_note = (
                f"fallback lossless_text (semantic_general J={semantic_j} below {adapt_floor})"
            )

    selected["adapt_note"] = adapt_note
    return selected, expanded_text, jaccard, loss_profile_used


def build_tier3_document(
    root: Path,
    *,
    lane: str,
    routing_profile: str = "track_a_promoted",
    adapt_loss_profile: bool = True,
    from_agent: str = "cursor_chat_source",
    to_agent: str = "cursor_chat_peer",
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)
    inject_text = _lane_inject_text(root, lane)
    overlay_terms = _lane_must_keep_overlay_terms(root, lane)
    inject_row = count_tokens(inject_text)
    inject_tokens = int(inject_row.get("tokens") or 0)
    paths = lane_artifact_paths(root, lane)

    client = TestClient(app)
    compress_row, expanded_text, expand_jaccard, loss_profile_used = _adaptive_compress(
        client,
        inject_text,
        lane=lane,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        adapt_loss_profile=adapt_loss_profile,
        must_keep_overlay_terms=overlay_terms or None,
    )

    decision = compress_row.get("decision")
    metrics = compress_row.get("compression_metrics") or {}
    expand_ok = decision == "compressed" and expand_jaccard is not None
    wire_token_out = metrics.get("token_out")
    wire_savings = metrics.get("savings_ratio")
    pilot_ok = bool(inject_tokens > 0 and decision == "compressed" and expand_ok)

    brief_rel = paths["brief"].relative_to(root).as_posix()
    peer_handoff = {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "lane": lane,
        "content_fingerprint": compress_row.get("content_fingerprint"),
        "trust_packet_artifact": paths["packet"].relative_to(root).as_posix(),
        "brief_artifact": brief_rel,
        "human_resume_unchanged": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
        "peer_chat_instruction": (
            f"Parallel Cursor chat (@{brief_rel}) instead of pasting full MISSION_LOG. SEND_GATE: HOLD."
        ),
    }

    return {
        "schema": "a2a_tier3_cursor_wire_handoff_pilot_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "tier": "tier3_cursor_parallel_chat",
        "target_point_id": "tp01_cursor_ops_resume_handoff",
        "status": "PILOT",
        "pilot_ok": pilot_ok,
        "boundary_ack": (
            "[HYPO] Tier 3 — one-lane Cursor parallel chat wire handoff pilot. "
            "Trust Packet expand for peer context only. Not production bus. Not SEND."
        ),
        "options": {
            "lane": lane,
            "routing_profile": routing_profile,
            "loss_profile_used": loss_profile_used,
            "adapt_loss_profile": adapt_loss_profile,
            "jaccard_adapt_floor": LANE_JACCARD_ADAPT_FLOOR.get(lane, JACCARD_ADAPT_FLOOR),
            "must_keep_overlay_term_count": len(overlay_terms),
            "from_agent": from_agent,
            "to_agent": to_agent,
        },
        "lane_artifacts": {k: v.relative_to(root).as_posix() for k, v in paths.items()},
        "l1_inject": {
            "char_count": len(inject_text),
            **inject_row,
            "preview_head": inject_text[:320] + ("..." if len(inject_text) > 320 else ""),
        },
        "l2_compress": compress_row,
        "peer_receive": {
            "expand_ok": expand_ok,
            "expanded_text_preview": expanded_text[:1200] + ("..." if len(expanded_text) > 1200 else ""),
            "jaccard_inject_vs_expanded": expand_jaccard,
            "original_text_on_expand_request": False,
        },
        "kpi_headline": {
            "inject_tokens": inject_tokens,
            "wire_token_out": wire_token_out,
            "wire_savings_ratio": wire_savings,
            "expand_jaccard": expand_jaccard,
            "decision": decision,
        },
        "peer_handoff": peer_handoff,
        "compress_skip_rules_applied": skip_rules,
        "evidence_paths": [
            "scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py",
            "scripts/Invoke-MkmCursorSessionUpgrade_v1.ps1",
            "scripts/build_a2a_l2_shadow_measurement_v1.py",
        ],
    }


def render_brief_md(doc: dict[str, Any]) -> str:
    kpi = doc.get("kpi_headline") or {}
    peer = doc.get("peer_receive") or {}
    handoff = doc.get("peer_handoff") or {}
    opts = doc.get("options") or {}
    lane = opts.get("lane") or DEFAULT_LANE
    brief_path = handoff.get("brief_artifact") or f"docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
    return f"""# Tier 3 Cursor wire handoff brief — `{lane}` [HYPO]

**INTERNAL ONLY · B-track · SEND_GATE: HOLD** — peer parallel chat paste surface.

---

## Usage (parallel Cursor chat)

| Chat | What to use |
|------|-------------|
| **Source** (재개/업그레이드) | `@docs/final/artifacts/mkm_chat_resume_pack_latest.md` — **기존과 동일** |
| **Peer** (병렬 `{lane}`) | `@docs/final/artifacts/{brief_path.split('/')[-1]}` |

- **금지:** MISSION_LOG 통째 · Track A 47%를 A2A 헤드라인에 합치기 · SEND 자동 트리거
- **Fact-Lock:** stub v2 packet-only expand · loss_profile=`{opts.get('loss_profile_used')}` · 무손실 아님

---

## Lane: `{lane}`

| KPI | 값 |
|-----|-----|
| L1 inject tokens | **{kpi.get('inject_tokens')}** |
| L2 wire token_out | **{kpi.get('wire_token_out')}** |
| L2 savings | **{_pct(kpi.get('wire_savings_ratio'))}** |
| expand J (inject vs expanded) | **{kpi.get('expand_jaccard')}** |
| compress decision | `{kpi.get('decision')}` |

Fingerprint: `{handoff.get('content_fingerprint')}`

---

## Expanded context (peer agent — packet-only expand)

```
{peer.get('expanded_text_preview') or '(expand failed or skipped)'}
```

---

## Machine path

- Trust packet JSON: `{handoff.get('trust_packet_artifact')}`
- Pilot JSON: `{(doc.get('lane_artifacts') or {}).get('pilot', '')}`

---

*Generated {doc.get('generated_at_utc')} · `build_a2a_tier3_cursor_wire_handoff_pilot_v1.py`*
"""


def _append_log_row(log_path: Path, doc: dict[str, Any]) -> None:
    kpi = doc.get("kpi_headline") or {}
    opts = doc.get("options") or {}
    row = {
        "schema": "a2a_tier3_cursor_wire_handoff_log_v1",
        "measured_at_utc": doc.get("generated_at_utc"),
        "pilot_ok": doc.get("pilot_ok"),
        "lane": opts.get("lane"),
        "loss_profile_used": opts.get("loss_profile_used"),
        "inject_tokens": kpi.get("inject_tokens"),
        "wire_token_out": kpi.get("wire_token_out"),
        "wire_savings_ratio": kpi.get("wire_savings_ratio"),
        "expand_jaccard": kpi.get("expand_jaccard"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_packet_sidecar(doc: dict[str, Any], packet_path: Path) -> None:
    compress = doc.get("l2_compress") or {}
    packet = compress.get("trust_packet_redacted")
    opts = doc.get("options") or {}
    sidecar = {
        "schema": "a2a_tier3_cursor_wire_handoff_packet_v1",
        "generated_at_utc": doc.get("generated_at_utc"),
        "lane": opts.get("lane"),
        "loss_profile_used": opts.get("loss_profile_used"),
        "content_fingerprint": compress.get("content_fingerprint"),
        "trust_packet_redacted": packet,
        "research_only": True,
    }
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_lane_index(root: Path) -> dict[str, Any]:
    lanes: dict[str, Any] = {}
    for lane in sorted(LANE_OPS_PACKS.keys()):
        paths = lane_artifact_paths(root, lane)
        pilot_path = paths["pilot"]
        if not pilot_path.is_file():
            continue
        doc = json.loads(pilot_path.read_text(encoding="utf-8-sig"))
        kpi = doc.get("kpi_headline") or {}
        handoff = doc.get("peer_handoff") or {}
        lanes[lane] = {
            "pilot_ok": doc.get("pilot_ok"),
            "brief_artifact": handoff.get("brief_artifact"),
            "expand_jaccard": kpi.get("expand_jaccard"),
            "wire_savings_ratio": kpi.get("wire_savings_ratio"),
            "loss_profile_used": (doc.get("options") or {}).get("loss_profile_used"),
            "generated_at_utc": doc.get("generated_at_utc"),
        }
    return {
        "schema": "a2a_tier3_cursor_wire_handoff_lane_index_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "lane_count": len(lanes),
        "lanes": lanes,
        "peer_index_md": DEFAULT_INDEX_MD.relative_to(root).as_posix(),
    }


def render_lane_index_md(index: dict[str, Any]) -> str:
    lines = [
        "# Tier 3 Cursor wire handoff — lane index [HYPO]",
        "",
        f"- generated: `{index.get('generated_at_utc')}`",
        "- SEND_GATE: HOLD",
        "",
        "| lane | brief | expand J | L2 savings | loss_profile |",
        "|------|-------|----------:|-----------:|--------------|",
    ]
    for lane, row in sorted((index.get("lanes") or {}).items()):
        brief = row.get("brief_artifact") or ""
        j = row.get("expand_jaccard")
        s = row.get("wire_savings_ratio")
        lp = row.get("loss_profile_used") or ""
        lines.append(
            f"| {lane} | `{brief}` | {j} | {_pct(s)} | {lp} |"
        )
    lines.extend(["", "Peer chat: `@docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_<lane>_v1_latest.md`"])
    return "\n".join(lines) + "\n"


def write_lane_index(root: Path) -> None:
    index = build_lane_index(root)
    DEFAULT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DEFAULT_INDEX_MD.write_text(render_lane_index_md(index), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", choices=sorted(LANE_OPS_PACKS.keys()), default=DEFAULT_LANE)
    ap.add_argument("--routing-profile", default="track_a_promoted")
    ap.add_argument("--no-adapt-loss-profile", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--brief-out", type=Path, default=None)
    ap.add_argument("--packet-out", type=Path, default=None)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--skip-lane-index", action="store_true")
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    paths = lane_artifact_paths(ROOT, args.lane)
    brief_out = args.brief_out or paths["brief"]
    packet_out = args.packet_out or paths["packet"]
    pilot_lane_out = paths["pilot"]

    doc = build_tier3_document(
        ROOT,
        lane=args.lane,
        routing_profile=args.routing_profile,
        adapt_loss_profile=not args.no_adapt_loss_profile,
    )
    for out_path in (args.out, pilot_lane_out):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_out.write_text(render_brief_md(doc), encoding="utf-8")
    _write_packet_sidecar(doc, packet_out)

    if args.append_log:
        _append_log_row(args.log, doc)
    if not args.skip_lane_index:
        write_lane_index(ROOT)

    kpi = doc.get("kpi_headline") or {}
    print(f"WROTE: {args.out}")
    print(f"WROTE: {pilot_lane_out}")
    print(f"WROTE: {brief_out}")
    print(f"WROTE: {packet_out}")
    print(
        f"pilot_ok={doc.get('pilot_ok')} lane={args.lane} "
        f"inject={kpi.get('inject_tokens')} wire_out={kpi.get('wire_token_out')} "
        f"jaccard={kpi.get('expand_jaccard')} loss_profile={(doc.get('options') or {}).get('loss_profile_used')}"
    )
    if args.append_log:
        print(f"APPENDED: {_log_path_display(ROOT, args.log)}")

    if args.strict_exit and not doc.get("pilot_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
