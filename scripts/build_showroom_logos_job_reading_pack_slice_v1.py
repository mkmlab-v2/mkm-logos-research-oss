#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build public showroom Job reading-pack slice from topology sidecar + verify gate ([HYPO]/NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.showroom_public_export_guard_v1 import scan_forbidden  # noqa: E402

DEFAULT_TOPOLOGY = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
DEFAULT_VERIFY_CHAIN = ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/showroom_logos_job_reading_pack_slice_v1.schema.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_job_reading_pack_slice_v1.json"
)
DEFAULT_MIRROR = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "no_trade_signals": True,
    "note_ko": (
        "욥기 reading pack 3종 연구 스냅샷입니다. 종교·신학적 진리·투자·임상·실매매(Track A) 근거가 아니며 "
        "「왜 고난?」 인과 단답을 제공하지 않습니다. why_question_assembled=false."
    ),
}

EXCERPT_MAX = 1200

INTERNAL_PATH_RE = re.compile(r"`?docs/[a-zA-Z0-9_./\\-]+`?", re.I)


def _sanitize_public_text(text: str) -> str:
    text = INTERNAL_PATH_RE.sub("[internal-ssot]", text)
    text = re.sub(r"scripts/[a-zA-Z0-9_./\\-]+\.py", "[internal-script]", text, flags=re.I)
    return text


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _md_excerpt(md_path: Path, *, max_chars: int = EXCERPT_MAX) -> str:
    text = md_path.read_text(encoding="utf-8")
    lines: list[str] = []
    in_body = False
    for line in text.splitlines():
        if line.startswith("# Logos Job"):
            in_body = True
            continue
        if not in_body:
            continue
        if line.startswith("## SSOT") or line.startswith("## VII. SSOT"):
            break
        if line.strip() == "---":
            continue
        if line.startswith("#"):
            lines.append(line.lstrip("#").strip())
        else:
            lines.append(line)
    body = "\n".join(lines).strip()
    body = re.sub(r"\[HYPO\]", "[HYPO]", body)
    if len(body) > max_chars:
        body = body[: max_chars - 1].rstrip() + "…"
    return _sanitize_public_text(body)


def _public_narrative_route(topo: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in topo.get("narrative_route") or []:
        rows.append(
            {
                "stage_id": stage.get("stage_id"),
                "order": stage.get("order"),
                "label_ko": stage.get("label_ko"),
                "bottleneck_ko": stage.get("bottleneck_ko"),
                "verse_refs": list(stage.get("verse_refs") or []),
            }
        )
    return rows


def _public_anchor_nodes(topo: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in topo.get("anchor_matrix") or []:
        rows.append(
            {
                "node_id": node.get("node_id"),
                "label_ko": node.get("label_ko"),
                "closed_system_ko": node.get("closed_system_ko"),
                "open_system_ko": node.get("open_system_ko"),
            }
        )
    return rows


def _public_bridge(topo: dict[str, Any]) -> dict[str, Any]:
    bridge = topo.get("bridge_pivot") or {}
    return {
        "verse_ref": bridge.get("verse_ref"),
        "label_ko": bridge.get("label_ko"),
        "reading_ko": bridge.get("reading_ko"),
    }


def _highlight_presets(topo: dict[str, Any]) -> list[dict[str, Any]]:
    stage_ids = [str(s.get("stage_id") or "") for s in topo.get("narrative_route") or []]
    pack_ids = [str(p.get("pack_id") or "") for p in topo.get("reading_pack") or []]
    return [
        {
            "preset_id": "job_suffering_reason",
            "label_ko": "욥 — 고난·의회·scope reset",
            "keywords_ko": ["욥", "고난", "의회", "scope", "bridge", "회복"],
            "pack_ids": pack_ids,
            "narrative_stage_ids": stage_ids,
        },
        {
            "preset_id": "existential_suffering",
            "label_ko": "실존적 고난 (데모)",
            "keywords_ko": ["실존", "고난", "교착", "침묵"],
            "pack_ids": ["integrated_topology", "scope_reset_no_why"],
            "narrative_stage_ids": [
                "human_debate_loop",
                "divine_speech_grid",
                "epilogue_closure",
            ],
        },
    ]


def build_slice(
    *,
    topology_path: Path,
    verify_chain_path: Path,
    require_verify_ok: bool = True,
) -> dict[str, Any]:
    if not topology_path.is_file():
        raise FileNotFoundError(f"topology missing: {topology_path}")

    ingested = _load(topology_path)
    topo = ingested.get("topology") or {}
    if ingested.get("send_gate") != "HOLD":
        raise ValueError("topology sidecar send_gate must be HOLD")
    if (topo.get("intentional_causal_gap") or {}).get("why_question_assembled") is not False:
        raise ValueError("why_question_assembled must be false")

    verify_ok = False
    if verify_chain_path.is_file():
        chain = _load(verify_chain_path)
        verify_ok = chain.get("ok") is True and chain.get("send_gate") == "HOLD"
    if require_verify_ok and not verify_ok:
        raise ValueError("reading_pack_verify_chain ok=true required (run verify chain first)")

    packs_out: list[dict[str, Any]] = []
    for pack in topo.get("reading_pack") or []:
        md_rel = pack.get("deep_synthesis_md_path")
        if not md_rel:
            raise ValueError(f"pack {pack.get('pack_id')} missing deep_synthesis_md_path")
        md_path = ROOT / str(md_rel)
        if not md_path.is_file():
            raise FileNotFoundError(f"deep synthesis md missing: {md_path}")
        packs_out.append(
            {
                "pack_id": pack.get("pack_id"),
                "label_ko": pack.get("label_ko"),
                "summary_ko": pack.get("summary_ko"),
                "utterance_class": pack.get("utterance_class"),
                "card_excerpt_ko": _md_excerpt(md_path),
            }
        )

    now = datetime.now(timezone.utc).replace(microsecond=0)
    stale = now + timedelta(days=7)
    return {
        "schema_version": "showroom_logos_job_reading_pack_slice_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stale_after_utc": stale.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "why_question_assembled": False,
        "disclaimer": DISCLAIMER,
        "query_id": topo.get("query_id"),
        "query_ko": topo.get("query_ko"),
        "anchor_ref": ingested.get("anchor_ref") or topo.get("anchor_ref"),
        "export_gate": {
            "reading_pack_verify_ok": verify_ok,
            "topology_send_gate": ingested.get("send_gate"),
        },
        "reading_packs": packs_out,
        "narrative_route_public": _public_narrative_route(topo),
        "anchor_nodes_public": _public_anchor_nodes(topo),
        "bridge_pivot_public": _public_bridge(topo),
        "highlight_presets": _highlight_presets(topo),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build showroom Job reading-pack slice JSON")
    ap.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    ap.add_argument("--verify-chain", type=Path, default=DEFAULT_VERIFY_CHAIN)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mirror-artifact", type=Path, default=DEFAULT_MIRROR)
    ap.add_argument("--no-mirror-artifact", action="store_true")
    ap.add_argument(
        "--skip-verify-gate",
        action="store_true",
        help="Allow export when verify chain missing (dev only)",
    )
    args = ap.parse_args()

    if not args.schema.is_file():
        print(f"schema missing: {args.schema}", file=sys.stderr)
        return 2

    try:
        doc = build_slice(
            topology_path=args.topology,
            verify_chain_path=args.verify_chain,
            require_verify_ok=not args.skip_verify_gate,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    violations = scan_forbidden(doc)
    if violations:
        print("export guard failed:", file=sys.stderr)
        print("\n".join(violations[:20]), file=sys.stderr)
        return 1

    try:
        _validate(doc, args.schema)
    except Exception as exc:  # noqa: BLE001
        print(f"schema validation failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(
        f"Wrote {args.out_json} packs={len(doc['reading_packs'])} "
        f"verify_ok={doc['export_gate']['reading_pack_verify_ok']}"
    )

    if not args.no_mirror_artifact and args.mirror_artifact:
        args.mirror_artifact.parent.mkdir(parents=True, exist_ok=True)
        args.mirror_artifact.write_text(text, encoding="utf-8")
        print(f"Mirrored {args.mirror_artifact}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
