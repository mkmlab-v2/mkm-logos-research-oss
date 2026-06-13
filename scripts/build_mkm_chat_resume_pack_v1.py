from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from mkm_ops_memory_index_lib_v1 import (
    COMMANDER_SLICE_NODE_IDS,
    DEFAULT_INDEX_PATH,
    LANE_OPS_PACKS,
    assemble_ops_memory_repair_v2_text,
    extract_node_from_index,
    nodes_for_resume,
    truncate_anchor_slice,
    utc_now_iso,
)
from mkm_long_term_memory_graph_lib_v1 import (
    DEFAULT_GRAPH_PATH,
    load_graph,
    merge_graph_routing_summary,
    nodes_for_topic_resume,
)
from mkm_sidecar_constitution_lib_v1 import (
    CONSTITUTION_REL,
    DEFAULT_SIDECAR_PATH,
    constitution_pins_for_resume,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_ops_inject_text(pins: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for pin in pins:
        parts.append(pin.get("essence") or "")
        for tag in pin.get("must_keep_tags") or []:
            parts.append(tag)
        slice_preview = pin.get("slice_preview")
        if slice_preview:
            parts.append(slice_preview)
    return "\n".join(parts)


def _synthetic_repair_query(
    routed: list[tuple[str, dict[str, Any]]],
    *,
    topic: str = "",
) -> str:
    parts: list[str] = []
    if topic.strip():
        parts.append(topic.strip())
    for _node_id, node in routed:
        essence = node.get("essence")
        if essence:
            parts.append(str(essence))
        for tag in node.get("must_keep_tags") or []:
            parts.append(str(tag))
    return " ".join(parts)


def _load_nl_ltm_sync_status(root: Path) -> Dict[str, Any] | None:
    path = root / "reports" / "notebooklm_ltm_graph_ops_push_result_v1_latest.json"
    if not path.is_file():
        return None
    doc = _read_json(path)
    if doc.get("schema") != "notebooklm_ltm_graph_ops_push_result_v1":
        return None
    ok = int(doc.get("ok") or 0)
    fail = int(doc.get("fail") or 0)
    return {
        "notebook_name": "01 · 지휘·운영",
        "notebook_id": doc.get("notebook_id"),
        "push_ok": ok,
        "push_fail": fail,
        "generated_at_utc": doc.get("generated_at_utc"),
        "repro_push": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts\\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1 -PushNlm"
        ),
        "nl_mcp_note": "Read 참모 — 통과 판정은 Cursor exit 0만",
    }


def _load_ops_pins(
    root: Path,
    *,
    top_n: int,
    lane: str | None,
    commander_default: bool,
    include_slice: bool,
    repair_v2_slice: bool,
    slice_max_chars: int,
    topic: str = "",
) -> tuple[List[Dict[str, Any]], str | None]:
    index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
    if not index_path.is_file():
        return [], None
    index = _read_json(index_path)
    graph_path = root / DEFAULT_GRAPH_PATH.relative_to(SCRIPT_ROOT)
    graph = _read_json(graph_path) if graph_path.is_file() else {}
    if graph.get("schema") == "mkm_long_term_memory_graph_v1" and (
        topic.strip() or lane
    ):
        routed = nodes_for_topic_resume(
            index,
            graph,
            topic,
            lane=lane,
            top_n=top_n,
            root=root,
        )
    else:
        routed = list(
            nodes_for_resume(
                index,
                top_n=top_n,
                lane=lane,
                root=root,
                commander_default=commander_default,
            )
        )
    pins: List[Dict[str, Any]] = []
    repair_v2_text: str | None = None
    for node_id, node in routed:
        pin: Dict[str, Any] = {
            "node_id": node_id,
            "essence": node.get("essence"),
            "must_keep_tags": node.get("must_keep_tags") or [],
            "file_path": node.get("file_path"),
            "line_range": node.get("line_range"),
        }
        if repair_v2_slice:
            pin["slice_mode"] = "repair_v2"
            pin["slice_max_chars"] = slice_max_chars
        elif commander_default and node_id in COMMANDER_SLICE_NODE_IDS:
            block = extract_node_from_index(root, node)
            preview, truncated = truncate_anchor_slice(
                block, max_chars=slice_max_chars
            )
            pin["slice_preview"] = preview
            pin["slice_truncated"] = truncated
            pin["slice_max_chars"] = slice_max_chars
            pin["slice_mode"] = "commander_default"
        elif include_slice:
            block = extract_node_from_index(root, node)
            preview, truncated = truncate_anchor_slice(
                block, max_chars=slice_max_chars
            )
            pin["slice_preview"] = preview
            pin["slice_truncated"] = truncated
            pin["slice_max_chars"] = slice_max_chars
            pin["slice_mode"] = "raw_truncate"
        pins.append(pin)
    if repair_v2_slice and routed:
        repair_v2_text = assemble_ops_memory_repair_v2_text(
            root,
            routed,
            slice_max_chars=slice_max_chars,
            query=_synthetic_repair_query(routed, topic=topic),
        )
    return pins, repair_v2_text


def _load_constitution_pins(root: Path, *, top_n: int = 3) -> list[dict[str, Any]]:
    sidecar_path = root / DEFAULT_SIDECAR_PATH.relative_to(SCRIPT_ROOT)
    if not sidecar_path.is_file():
        return []
    sidecar = _read_json(sidecar_path)
    if sidecar.get("schema") != "mkm_sidecar_constitution_paths_v1":
        return []
    return constitution_pins_for_resume(sidecar, top_n=top_n)


def _load_a2a_chain_refs(root: Path) -> Dict[str, Any] | None:
    """Machine-only tp03 pointer block — omitted from human MD resume pack."""
    pilot_path = root / "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json"
    if not pilot_path.is_file():
        return None
    pilot = _read_json(pilot_path)
    if pilot.get("schema") != "a2a_tp03_chain_ref_pilot_v1":
        return None
    pointers: List[Dict[str, Any]] = []
    for row in pilot.get("artifacts") or []:
        handoff = row.get("pointer_handoff")
        if not isinstance(handoff, dict):
            continue
        slim: Dict[str, Any] = {
            "artifact_id": handoff.get("artifact_id") or row.get("artifact_id"),
            "artifact_path": handoff.get("artifact_path") or row.get("artifact_path"),
            "sha256": handoff.get("sha256") or row.get("sha256"),
            "chain_step": handoff.get("chain_step") or row.get("chain_step"),
            "handoff_mode": handoff.get("handoff_mode") or "pointer_plus_fingerprint",
        }
        if handoff.get("essence_line"):
            slim["essence_line"] = handoff["essence_line"]
        if handoff.get("schema"):
            slim["schema"] = handoff["schema"]
        pointers.append(slim)
    if not pointers:
        return None
    agg = pilot.get("aggregate_pointer_vs_full") or {}
    return {
        "schema": "mkm_chat_resume_a2a_chain_refs_v1",
        "source_pilot": "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json",
        "research_only": True,
        "boundary_ack": (
            "[HYPO] A2A machine block only — pointer+fingerprint refs for agent context. "
            "Human MD resume pack unchanged. Not Track A·live merge."
        ),
        "artifacts_present": pilot.get("artifacts_present"),
        "artifacts_missing": pilot.get("artifacts_missing"),
        "reduction_percent_if_pointers_only": (pilot.get("kpi_headline") or {}).get(
            "reduction_percent_if_pointers_only"
        ),
        "aggregate_pointer_vs_full": {
            "tokens_saved_sum": agg.get("tokens_saved_sum"),
            "reduction_percent": agg.get("reduction_percent"),
        },
        "pointer_rows": pointers,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument(
        "--include-slice",
        action="store_true",
        help="[HYPO] Include truncated anchor body per pin (Phase 0.5).",
    )
    ap.add_argument(
        "--repair-v2-slice",
        action="store_true",
        help="[HYPO] Assemble repair_v2 noise-guard slices (overrides --include-slice).",
    )
    ap.add_argument(
        "--topic",
        default="",
        help="Optional query/topic for repair_v2 relevance (lane routing uses --lane).",
    )
    ap.add_argument(
        "--slice-max-chars",
        type=int,
        default=1200,
        help="Max chars per anchor slice preview (default 1200).",
    )
    ap.add_argument(
        "--lane",
        choices=sorted(LANE_OPS_PACKS.keys()),
        default=None,
        help="Oracle/MS/Infra lane pack: board+CENTRAL+one lane row (ignores --top-n for ops pins).",
    )
    ap.add_argument(
        "--no-commander-default",
        action="store_true",
        help="Without --lane: use legacy top-N pins instead of board+CENTRAL+next-one table.",
    )
    ap.add_argument(
        "--append-l2-shadow",
        action="store_true",
        help="[HYPO] Tier 2: append L2 compress shadow log after pack write (human MD unchanged).",
    )
    args = ap.parse_args()

    if args.slice_max_chars < 64:
        print("FAIL: --slice-max-chars must be >= 64", file=sys.stderr)
        return 1

    root = SCRIPT_ROOT
    art = root / "docs" / "final" / "artifacts"

    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")

    use_repair_v2 = args.repair_v2_slice
    use_raw_slice = args.include_slice and not use_repair_v2
    commander_default = args.lane is None and not args.no_commander_default
    ops_pins, repair_v2_text = _load_ops_pins(
        root,
        top_n=args.top_n,
        lane=args.lane,
        commander_default=commander_default,
        include_slice=use_raw_slice,
        repair_v2_slice=use_repair_v2,
        slice_max_chars=args.slice_max_chars,
        topic=args.topic,
    )
    graph_path = root / DEFAULT_GRAPH_PATH.relative_to(SCRIPT_ROOT)
    graph = _read_json(graph_path) if graph_path.is_file() else {}
    constitution_pins = _load_constitution_pins(root, top_n=min(3, args.top_n))
    a2a_chain_refs = _load_a2a_chain_refs(root)
    ltm_routing = None
    if graph.get("schema") == "mkm_long_term_memory_graph_v1" and args.topic.strip():
        ltm_routing = merge_graph_routing_summary(
            graph, args.topic, resolved_lane=args.lane
        )
    inject_text = (
        repair_v2_text
        if repair_v2_text is not None
        else _build_ops_inject_text(ops_pins)
    )
    if constitution_pins:
        for pin in constitution_pins:
            inject_text += "\n" + (pin.get("essence") or "")
            for tag in pin.get("must_keep_tags") or []:
                inject_text += "\n" + tag

    if ops_pins and inject_text:
        index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
        gate_cmd = [
            sys.executable,
            str(root / "scripts" / "check_mkm_ops_memory_must_keep_gate_v1.py"),
            "--phase",
            "inject",
            "--index",
            str(index_path),
            "--payload-text",
            inject_text,
        ]
        for pin in ops_pins:
            gate_cmd.extend(["--node-id", pin["node_id"]])
        proc = subprocess.run(gate_cmd, capture_output=True, text=True, cwd=str(root))
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            print("FAIL: ops memory inject gate (phase=inject)", file=sys.stderr)
            return 1
        print("ops memory inject gate (phase=inject): OK")

    resume: Dict[str, Any] = {
        "schema": "mkm_chat_resume_pack_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] resume pack — ops index pins are B-track; no Track A·live merge",
        "ops_memory_options": {
            "include_slice": use_raw_slice,
            "repair_v2_slice": use_repair_v2,
            "commander_default": commander_default,
            "commander_trigger_ko": "장기기억 맥락이어",
            "slice_max_chars": args.slice_max_chars
            if (use_raw_slice or use_repair_v2 or commander_default)
            else None,
            "topic": args.topic or None,
            "top_n": args.top_n,
            "lane": args.lane,
        },
        "commander_briefing": {
            "trigger_ko": "장기기억 맥락이어",
            "mission_log_mode": "next_one_table_pin_only — never paste full MISSION_LOG.md",
            "fact_lock": "CONSTITUTION + scripts + exit 0 only — NL answer is not pass/fail",
            "send_gate": "HOLD",
            "nl_ltm_sync": _load_nl_ltm_sync_status(root),
        },
        "quick_refs": {
            "central_memory": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "ops_memory_index": "storage/meta/mkm_ops_memory_index_v1.json",
            "long_term_memory_graph": "storage/meta/mkm_long_term_memory_graph_v1.json",
            "ops_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "ops_dashboard_exec_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md",
            "acceptance_json": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "runbook_checklist_md": "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md",
            "core_prompt_gemini_athena": "docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V1.md",
        },
        "ops_memory_pins": ops_pins,
        "constitution_path_pins": constitution_pins,
        "constitution_sidecar_path": str(
            DEFAULT_SIDECAR_PATH.relative_to(SCRIPT_ROOT)
        ).replace("\\", "/"),
        "constitution_source_ssot": CONSTITUTION_REL,
        "long_term_memory_routing": ltm_routing,
        "a2a_chain_refs": a2a_chain_refs,
        "latest_status": {
            "system_status": (dashboard.get("system") or {}).get("status"),
            "promotion_decision": (dashboard.get("system") or {}).get("promotion_decision"),
            "trackc_packet_status": (dashboard.get("trackc") or {}).get("packet_status"),
            "acceptance_status": acceptance.get("status"),
        },
        "resume_commands": [
            "py scripts/build_mkm_long_term_memory_graph_v1.py",
            "py scripts/build_mkm_ops_memory_index_v1.py",
            "py scripts/build_mkm_ops_memory_doctrine_overlay_v1.py",
            "py scripts/build_mkm_chat_resume_pack_v1.py --repair-v2-slice",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -RepairV2Slice",
        ],
    }

    out_json = art / "mkm_chat_resume_pack_latest.json"
    out_md = art / "mkm_chat_resume_pack_latest.md"
    out_json.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM Chat Resume Pack",
        "",
        f"- generated_at_utc: `{resume['generated_at_utc']}`",
        f"- research_only: `{resume.get('research_only')}`",
        f"- include_slice: `{use_raw_slice}`",
        f"- repair_v2_slice: `{use_repair_v2}`",
        f"- system_status: `{resume['latest_status'].get('system_status')}`",
        f"- promotion_decision: `{resume['latest_status'].get('promotion_decision')}`",
        f"- trackc_packet_status: `{resume['latest_status'].get('trackc_packet_status')}`",
        f"- acceptance_status: `{resume['latest_status'].get('acceptance_status')}`",
        "",
    ]
    briefing = resume.get("commander_briefing") or {}
    if briefing:
        md_lines += [
            "## Commander Resume (`장기기억 맥락이어`)",
            "",
            f"- trigger: `{briefing.get('trigger_ko')}`",
            f"- mission_log: {briefing.get('mission_log_mode')}",
            f"- fact_lock: {briefing.get('fact_lock')}",
            f"- SEND_GATE: `{briefing.get('send_gate')}`",
        ]
        nl_sync = briefing.get("nl_ltm_sync") or {}
        if nl_sync:
            md_lines.append(
                f"- NL 지휘부 sync: push **{nl_sync.get('push_ok')}/{int(nl_sync.get('push_ok') or 0) + int(nl_sync.get('push_fail') or 0)}** "
                f"@ `{nl_sync.get('generated_at_utc')}` · repro: `{nl_sync.get('repro_push')}`"
            )
        md_lines.append("")
    if ops_pins:
        md_lines += ["## Ops Memory Pins ([HYPO])", ""]
        for pin in ops_pins:
            tags = ", ".join(f"`{t}`" for t in pin.get("must_keep_tags") or [])
            md_lines.append(
                f"- **{pin['node_id']}** — {pin.get('essence')} · must_keep: {tags}"
            )
            if pin.get("slice_preview"):
                truncated = pin.get("slice_truncated")
                md_lines.append(
                    f"  - slice_preview ({'truncated' if truncated else 'full'}):"
                )
                md_lines.append("```")
                md_lines.append(pin["slice_preview"])
                md_lines.append("```")
        md_lines.append("")

    if constitution_pins:
        md_lines += ["## Constitution Path Pins ([HYPO] sidecar)", ""]
        for pin in constitution_pins:
            tags = ", ".join(f"`{t}`" for t in pin.get("must_keep_tags") or [])
            paths = ", ".join(f"`{p}`" for p in pin.get("top_paths") or [])[:500]
            md_lines.append(
                f"- **{pin['segment_id']}** — {pin.get('essence')} · must_keep: {tags}"
            )
            if paths:
                md_lines.append(f"  - paths: {paths}")
        md_lines.append("")

    md_lines += ["## Quick Refs"]
    for _, path in resume["quick_refs"].items():
        md_lines.append(f"- `{path}`")
    md_lines += [
        "",
        "## Resume Commands",
        "- `py scripts/build_mkm_ops_memory_index_v1.py`",
        "- `py scripts/build_mkm_chat_resume_pack_v1.py --include-slice`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"resume pack json written: {out_json}")
    print(f"resume pack md written: {out_md}")

    if args.append_l2_shadow:
        from build_a2a_l2_shadow_measurement_v1 import (  # noqa: E402
            DEFAULT_LOG,
            DEFAULT_OUT,
            _append_log_row,
            build_shadow_document,
        )

        shadow_doc = build_shadow_document(
            root,
            lane=args.lane,
            top_n=args.top_n,
        )
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT.write_text(
            json.dumps(shadow_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _append_log_row(DEFAULT_LOG, shadow_doc)
        headline = shadow_doc.get("kpi_headline") or {}
        print(
            f"l2 shadow: ok={shadow_doc.get('shadow_ok')} "
            f"inject={headline.get('inject_tokens')} "
            f"l2_savings={headline.get('l2_savings_ratio')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
