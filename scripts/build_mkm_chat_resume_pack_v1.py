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
from mkm_agent_mistake_registry_lib_v1 import (  # noqa: E402
    DEFAULT_REGISTRY,
    guardrail_lines,
    query_guardrails,
)
from mkm_mistake_guardrail_yaml_v1 import guardrail_inject_block_v1_1  # noqa: E402
from mkm_cursor_self_audit_lib_v1 import lane_default_topic_query
from mkm_sidecar_constitution_lib_v1 import (
    CONSTITUTION_REL,
    DEFAULT_SIDECAR_PATH,
    constitution_pins_for_resume,
)
from mkm_resume_pin_freshness_v1 import (  # noqa: E402
    annotate_ops_pins_freshness,
    build_freshness_report,
    write_freshness_latest,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
LOGOS_WIRING_REL = "docs/final/artifacts/logos_theory_implementation_wiring_v1.json"
ORACLE_MODULE_RULE = ".cursor/rules/logos-oracle-module-tier2-prep-v1.mdc"
TIER1_READINESS_REL = "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
TIER2_PROTOCOL_REL = "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"
TIER3_PROTOCOL_REL = "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
TIER2_MANIFEST_REL = "reports/logos_oracle_tier2_cursor_inject_manifest_v1_latest.json"
A2A_ORACLE_BRIEF_REL = "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_oracle_v1_latest.md"
NARRATIVE_OBS_REL = "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"
ORACLE_MODULE_EDGE_IDS = (
    "oracle_cursor_inject_tier1_readiness",
    "oracle_tier2_incremental_append_protocol",
    "oracle_tier3_narrative_upgrade_protocol",
    "oracle_narrative_closure_observability",
    "han_vocology_km_vhi_pilot_observability",
)
COMMANDER_TRIGGERS_REL = "docs/final/artifacts/mkm_commander_resume_triggers_v1.json"
COMMANDER_CHAT_TONE_REL = "docs/final/artifacts/commander_chat_tone_prefs_v1_latest.json"
SEND_GATE_VOCAB_REL = "docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json"


def _load_commander_chat_tone(root: Path) -> Dict[str, Any]:
    path = root / COMMANDER_CHAT_TONE_REL
    if not path.is_file():
        return {}
    doc = _read_json(path)
    return doc if doc.get("schema") == "commander_chat_tone_prefs_v1" else {}


def _promotion_decision_agent_label(decision: str | None) -> str | None:
    if not decision:
        return None
    labels = {
        "GO_FINAL_V2": "INTERNAL_V2_READY",
        "HOLD": "HOLD",
        "GO": "INTERNAL_GO",
        "NO_GO": "NO_GO",
    }
    return labels.get(str(decision), str(decision))

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


def _load_cursor_host_hygiene(root: Path) -> Dict[str, Any] | None:
    path = root / "reports" / "cursor_host_hygiene_latest.json"
    if not path.is_file():
        return None
    doc = _read_json(path)
    if doc.get("schema") != "cursor_host_hygiene_v1":
        return None
    return doc


def _cursor_host_alert_lines(hygiene: Dict[str, Any] | None) -> List[str]:
    if not hygiene:
        return []
    if not (hygiene.get("degraded") or hygiene.get("reload_required")):
        return []
    reasons = hygiene.get("reasons") or []
    reason_text = "; ".join(str(r) for r in reasons[:4]) or "see hygiene json"
    return [
        "> **[!] ATTENTION: Cursor Reload Required** — host hygiene degraded "
        f"({reason_text}). Quit Cursor fully, then **Reload Window** or restart. "
        "SSOT: `reports/cursor_host_hygiene_latest.json`.",
        "",
    ]


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


def _load_commander_resume_triggers(root: Path) -> Dict[str, Any]:
    path = root / COMMANDER_TRIGGERS_REL
    if not path.is_file():
        return {}
    doc = _read_json(path)
    return doc if doc.get("schema") == "mkm_commander_resume_triggers_v1" else {}


def _where_used_resume_link(root: Path, topic: str) -> Dict[str, Any] | None:
    """Thin where-used → resume link when --topic matches registry (SSOT paths only)."""
    topic = (topic or "").strip()
    if not topic:
        return None
    scripts_dir = root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from mkm_where_used_v1_lib import load_registry, resolve_topic  # noqa: E402
    except ImportError:
        return None
    reg_path = root / "docs/final/artifacts/mkm_where_used_registry_v1.json"
    if not reg_path.is_file():
        return None
    try:
        doc = load_registry(reg_path)
    except (OSError, json.JSONDecodeError):
        return None
    topics = doc.get("topics") or {}
    key = topic if topic in topics else None
    if key is None:
        lowered = {str(k).lower(): k for k in topics}
        key = lowered.get(topic.lower())
    if key is None:
        return None
    try:
        report = resolve_topic(str(key), registry=doc)
    except KeyError:
        return None
    return {
        "schema": "mkm_chat_resume_where_used_link_v1",
        "topic": report.get("topic"),
        "label_ko": report.get("label_ko"),
        "registry": report.get("registry"),
        "coverage_ok": report.get("coverage_ok"),
        "ssot_paths": list(report.get("paths_hit") or [])[:12],
        "axes_hit": report.get("axes_hit"),
        "axes_required": report.get("axes_required"),
        "ops_pin_id": report.get("ops_pin_id"),
        "reproduce": report.get("reproduce"),
        "research_only": True,
        "send_gate": "HOLD",
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
        "--infer-topic-from-lane",
        action="store_true",
        help="When --lane set and --topic empty: build LTM graph query from lane topic hints.",
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
        "--resume-mode",
        choices=["standard", "advanced_logos"],
        default="standard",
        help="Commander trigger mode: standard vs Logos advanced interp (forces --lane oracle).",
    )
    ap.add_argument(
        "--append-l2-shadow",
        action="store_true",
        help="[HYPO] Tier 2: append L2 compress shadow log after pack write (human MD unchanged).",
    )
    ap.add_argument(
        "--mistake-registry",
        type=Path,
        default=None,
        help="Grounded mistake registry JSONL for [MISTAKE GUARDRAIL] inject.",
    )
    ap.add_argument("--mistake-guardrail-limit", type=int, default=None)
    ap.add_argument(
        "--mistake-guardrail-lane",
        default=None,
        help="Lane filter for mistake guardrails (defaults to --lane or infra).",
    )
    ap.add_argument(
        "--guardrail-format",
        choices=["md", "yaml", "both"],
        default="both",
        help="Mistake guardrail inject: prose bullets (md), YAML block (yaml), or both (v1.1 default).",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional alternate JSON output path (validate loop).",
    )
    ap.add_argument(
        "--skip-ops-gate",
        action="store_true",
        help="Skip ops memory inject gate (validate loop only).",
    )
    args = ap.parse_args()

    if args.mistake_guardrail_limit is None:
        budget_path = SCRIPT_ROOT / "docs/final/artifacts/mkm_resume_inject_budget_v1_latest.json"
        limit = 3
        if budget_path.is_file():
            try:
                bdoc = json.loads(budget_path.read_text(encoding="utf-8"))
                limit = int((bdoc.get("budgets") or {}).get("max_mistake_guardrails") or 3)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                limit = 3
        args.mistake_guardrail_limit = max(1, limit)

    if args.resume_mode == "advanced_logos" and args.lane is None:
        args.lane = "oracle"

    if args.infer_topic_from_lane and args.lane and not args.topic.strip():
        args.topic = lane_default_topic_query(args.lane)

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
    pin_contradictions: list[dict[str, Any]] = []
    pin_l0_l2_gaps: list[dict[str, Any]] = []
    pin_freshness_report: dict[str, Any] | None = None
    if ops_pins:
        ops_pins, pin_contradictions, pin_l0_l2_gaps = annotate_ops_pins_freshness(
            ops_pins, root
        )
        pin_freshness_report = build_freshness_report(
            ops_pins,
            pin_contradictions,
            l0_l2_claim_gaps=pin_l0_l2_gaps,
        )
        try:
            write_freshness_latest(
                pin_freshness_report,
                root / "docs/final/artifacts/mkm_resume_pin_freshness_v1_latest.json",
            )
        except ValueError as exc:
            print(f"WARN: pin freshness artifact skipped: {exc}", file=sys.stderr)
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

    if ops_pins and inject_text and not args.skip_ops_gate:
        index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
        index_nodes = (_read_json(index_path).get("nodes") or {}) if index_path.is_file() else {}
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
            node_id = pin["node_id"]
            # Overlay pins (e.g. theory/json slices) may not exist in the base index file.
            # Gate only known nodes here; overlay tags are still present in inject_text itself.
            if node_id in index_nodes:
                gate_cmd.extend(["--node-id", node_id])
        proc = subprocess.run(gate_cmd, capture_output=True, text=True, cwd=str(root))
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            print("FAIL: ops memory inject gate (phase=inject)", file=sys.stderr)
            return 1
        print("ops memory inject gate (phase=inject): OK")

    cursor_host_hygiene = _load_cursor_host_hygiene(root)
    commander_triggers = _load_commander_resume_triggers(root)
    commander_chat_tone = _load_commander_chat_tone(root)
    active_mode = args.resume_mode
    mode_doc = (commander_triggers.get("modes") or {}).get(
        "advanced_logos_interp" if active_mode == "advanced_logos" else "standard"
    ) or {}
    end_mode_id = "advanced_logos_interp" if active_mode == "advanced_logos" else "standard"
    end_doc = (commander_triggers.get("session_end_modes") or {}).get(end_mode_id) or {}

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
            "trigger_ko": mode_doc.get("trigger_ko", ["장기기억 맥락이어"])[0]
            if mode_doc.get("trigger_ko")
            else "장기기억 맥락이어",
            "session_end_trigger_ko": end_doc.get("trigger_ko", ["마무리해줘"])[0]
            if end_doc.get("trigger_ko")
            else "마무리해줘",
            "pairing_ko": commander_triggers.get("pairing_ko"),
            "resume_mode": active_mode,
            "mode_id": mode_doc.get("mode_id", "standard"),
            "label_ko": mode_doc.get("label_ko"),
            "mission_log_mode": "next_one_table_pin_only — never paste full MISSION_LOG.md",
            "fact_lock": "CONSTITUTION + scripts + exit 0 only — NL answer is not pass/fail",
            "send_gate": "HOLD",
            "send_gate_vocab": SEND_GATE_VOCAB_REL,
            "promotion_decision_note": "INTERNAL_V2_READY = internal v2 readiness only — not SEND or live trading",
            "nl_ltm_sync": _load_nl_ltm_sync_status(root),
            "cursor_host_hygiene": cursor_host_hygiene,
            "chat_tone": {
                "ssot": COMMANDER_CHAT_TONE_REL,
                "routine_disclaimer_suppress": (
                    (commander_chat_tone.get("routine_disclaimer_suppress") or {}).get("enabled")
                ),
                "agent_contract_ko": commander_chat_tone.get("agent_contract_ko"),
            },
        },
        "commander_resume_triggers_ssot": COMMANDER_TRIGGERS_REL,
        "commander_chat_tone_ssot": COMMANDER_CHAT_TONE_REL,
        "send_gate_vocabulary_ssot": SEND_GATE_VOCAB_REL,
        "commander_chat_tone": commander_chat_tone or None,
        "commander_resume_mode": {
            "mode_id": mode_doc.get("mode_id", active_mode),
            "label_ko": mode_doc.get("label_ko"),
            "agent_contract_ko": mode_doc.get("agent_contract_ko"),
            "session_upgrade": mode_doc.get("session_upgrade"),
            "pipeline_steps": mode_doc.get("pipeline_steps"),
            "artifact_pointers": mode_doc.get("artifact_pointers"),
        }
        if mode_doc
        else {"mode_id": active_mode},
        "quick_refs": {
            "central_memory": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "ops_memory_index": "storage/meta/mkm_ops_memory_index_v1.json",
            "long_term_memory_graph": "storage/meta/mkm_long_term_memory_graph_v1.json",
            "ops_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "ops_dashboard_exec_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md",
            "acceptance_json": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "runbook_checklist_md": "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md",
            "core_prompt_gemini_athena": "docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V2.md",
            "gemini_web_staff_officer_contract": "docs/final/artifacts/MKM_GEMINI_WEB_STAFF_OFFICER_CONTRACT_V1.md",
            "gemini_web_staff_officer_paste": "docs/final/artifacts/MKM_GEMINI_WEB_STAFF_OFFICER_PASTE_V1.txt",
        },
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
            "promotion_decision_agent_label": _promotion_decision_agent_label(
                (dashboard.get("system") or {}).get("promotion_decision")
            ),
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
    resume["ops_memory_pins"] = ops_pins
    where_used_link = _where_used_resume_link(root, str(args.topic or ""))
    if where_used_link:
        resume["where_used"] = where_used_link
    if pin_freshness_report:
        resume["pin_freshness"] = {
            "schema": pin_freshness_report.get("schema"),
            "artifact": "docs/final/artifacts/mkm_resume_pin_freshness_v1_latest.json",
            "advisory_summary": pin_freshness_report.get("advisory_summary"),
            "checkpoint_contradiction_count": len(pin_contradictions),
            "l0_l2_claim_gap_count": len(pin_l0_l2_gaps),
            "l0_l2_claim_gaps": pin_l0_l2_gaps[:8],
            "reproduce": "py scripts/check_mkm_resume_pin_freshness_v1.py",
        }

    if args.lane == "oracle":
        resume["quick_refs"]["logos_theory_wiring"] = LOGOS_WIRING_REL
        resume["quick_refs"]["oracle_module_tier2_readiness"] = TIER1_READINESS_REL
        resume["quick_refs"]["oracle_tier2_protocol"] = TIER2_PROTOCOL_REL
        resume["quick_refs"]["oracle_tier3_protocol"] = TIER3_PROTOCOL_REL
        resume["quick_refs"]["oracle_tier2_manifest"] = TIER2_MANIFEST_REL
        resume["quick_refs"]["oracle_a2a_tier3_brief"] = A2A_ORACLE_BRIEF_REL
        resume["quick_refs"]["oracle_narrative_closure_observability"] = NARRATIVE_OBS_REL
        resume["quick_refs"]["oracle_module_cursor_rule"] = ORACLE_MODULE_RULE
        wiring_doc = _read_json(root / LOGOS_WIRING_REL)
        readiness_doc = _read_json(root / TIER1_READINESS_REL)
        tier2_doc = _read_json(root / TIER2_PROTOCOL_REL)
        tier3_doc = _read_json(root / TIER3_PROTOCOL_REL)
        observability_doc = _read_json(root / NARRATIVE_OBS_REL)
        snap = readiness_doc.get("tier2_pin_schema_snapshot") or {}
        resume["logos_theory_wiring"] = {
            "registry": LOGOS_WIRING_REL,
            "verify_command": wiring_doc.get("verify_command"),
            "edge_ids": [e.get("edge_id") for e in wiring_doc.get("canonical_edges") or []],
            "agent_rule_ko": wiring_doc.get("agent_rule_ko"),
        }
        resume["oracle_module_lane"] = {
            "cursor_rule": ORACLE_MODULE_RULE,
            "tier1_readiness": TIER1_READINESS_REL,
            "tier2_protocol": TIER2_PROTOCOL_REL,
            "tier3_protocol": TIER3_PROTOCOL_REL,
            "tier2_manifest": TIER2_MANIFEST_REL,
            "a2a_tier3_oracle_brief": A2A_ORACLE_BRIEF_REL,
            "narrative_closure_observability": NARRATIVE_OBS_REL,
            "send_gate": readiness_doc.get("send_gate"),
            "tier1_module_ssot_ready": readiness_doc.get("tier1_module_ssot_ready"),
            "tier2_prep_ready": readiness_doc.get("tier2_prep_ready"),
            "tier2_cursor_rules_full_upgrade_ready": readiness_doc.get(
                "tier2_cursor_rules_full_upgrade_ready"
            ),
            "tier3_constitution_narrative_full_upgrade_ready": readiness_doc.get(
                "tier3_constitution_narrative_full_upgrade_ready"
            ),
            "tier2_blockers_released": sum(
                1 for b in (tier2_doc.get("blocker_release_matrix") or []) if b.get("released")
            ),
            "tier3_blockers_released": sum(
                1 for b in (tier3_doc.get("blocker_release_matrix") or []) if b.get("released")
            ),
            "resonance_cap_read_only": snap.get("resonance_cap"),
            "hd_mission_version": snap.get("hd_mission_version"),
            "observation_pass": observability_doc.get("observation_pass"),
            "module_wiring_edge_ids": list(ORACLE_MODULE_EDGE_IDS),
            "weekly_routine": "scripts/Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1",
            "repro_commands": [
                "py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py --require-tier2-unlock",
                "py scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py",
                "py scripts/build_logos_oracle_tier2_cursor_inject_manifest_v1.py",
                "py scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py --skip-overlay-refresh",
                "py scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
                "py scripts/run_mkm_hd_oracle_module_vocology_chain_v1.py --skip-overlay-refresh",
            ],
        }
        resume["resume_commands"].insert(
            0, "py scripts/check_logos_theory_implementation_wiring_v1.py"
        )
        resume["resume_commands"].insert(
            0, "py scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py"
        )

    registry_path = args.mistake_registry or (root / DEFAULT_REGISTRY)
    guard_lane = args.mistake_guardrail_lane or args.lane or "infra"
    guard_records = query_guardrails(
        registry_path, lane=guard_lane, limit=max(1, args.mistake_guardrail_limit)
    )
    jema_wall_line = (
        "Field(regime_map+ops gates)만 Final Action; 사상=단기 톤 보조 [HYPO][NON_GATING]; "
        "Track A·임상·실매매·단정 트리거 금지."
    )
    guard_lines = [f"- {jema_wall_line}"] + guardrail_lines(guard_records)
    rel_registry = (
        str(registry_path.relative_to(root)).replace("\\", "/")
        if registry_path.is_relative_to(root)
        else str(registry_path).replace("\\", "/")
    )
    resume["jema_os_kernel"] = {
        "schema": "jema_os_kernel_resume_pointer_v1",
        "runner_policy": "docs/final/artifacts/jema_os_runner_policy_v1_latest.json",
        "domain_plugins": "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json",
        "mistake_registry": rel_registry,
        "kernel_chain": "py scripts/run_jema_os_kernel_chain_v1.py",
        "research_only": True,
        "send_gate": "HOLD",
    }
    gf = args.guardrail_format
    if gf == "md":
        resume["mistake_guardrails"] = {
            "schema": "mkm_mistake_guardrail_inject_v1",
            "format": "md",
            "registry_path": rel_registry,
            "lane": guard_lane,
            "lines": guard_lines,
            "record_count": len(guard_records),
        }
    else:
        block = guardrail_inject_block_v1_1(
            lane=guard_lane,
            registry_path=rel_registry,
            wall_lines=guard_lines,
            records=guard_records,
            prose_lines=guard_lines,
        )
        block["format"] = gf
        resume["mistake_guardrails"] = block

    out_json = args.out_json if args.out_json else art / "mkm_chat_resume_pack_latest.json"
    out_md = art / "mkm_chat_resume_pack_latest.md"
    out_json.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = _cursor_host_alert_lines(cursor_host_hygiene) + [
        "# MKM Chat Resume Pack",
        "",
        f"- generated_at_utc: `{resume['generated_at_utc']}`",
        f"- research_only: `{resume.get('research_only')}`",
        f"- include_slice: `{use_raw_slice}`",
        f"- repair_v2_slice: `{use_repair_v2}`",
        f"- system_status: `{resume['latest_status'].get('system_status')}`",
        f"- promotion_decision: `{resume['latest_status'].get('promotion_decision')}` "
        f"(agent: `{resume['latest_status'].get('promotion_decision_agent_label')}`)",
        f"- trackc_packet_status: `{resume['latest_status'].get('trackc_packet_status')}` "
        f"(artifact READY ≠ SEND; see SEND_GATE below)",
        f"- acceptance_status: `{resume['latest_status'].get('acceptance_status')}`",
        "",
    ]
    briefing = resume.get("commander_briefing") or {}
    if briefing:
        md_lines += [
            "## Commander Resume (`장기기억 맥락이어`)",
            "",
            f"- trigger: `{briefing.get('trigger_ko')}`",
            f"- session_end: `{briefing.get('session_end_trigger_ko', '마무리해줘')}`",
            f"- resume_mode: `{briefing.get('resume_mode', 'standard')}` · `{briefing.get('label_ko') or briefing.get('mode_id')}`",
            f"- mission_log: {briefing.get('mission_log_mode')}",
            f"- fact_lock: {briefing.get('fact_lock')}",
            f"- SEND_GATE: `{briefing.get('send_gate')}`",
        ]
        if briefing.get("send_gate_vocab"):
            md_lines.append(
                f"- send_gate_vocab: `{briefing.get('send_gate_vocab')}` "
                f"(narrative_lane_open ≠ SEND · promotion GO ≠ live)"
            )
        chat_tone = briefing.get("chat_tone") or {}
        if chat_tone.get("routine_disclaimer_suppress"):
            md_lines += [
                f"- chat_tone: routine live-trading disclaimer **suppress ON** · `{chat_tone.get('ssot')}`",
            ]
            if chat_tone.get("agent_contract_ko"):
                md_lines.append(f"- chat_tone_contract: {chat_tone.get('agent_contract_ko')}")
        mode_block = resume.get("commander_resume_mode") or {}
        if briefing.get("resume_mode") == "advanced_logos" and mode_block:
            md_lines += [
                "",
                "### Logos 고급 해석 모드 (`장기기억 맥락이어 고급해석`)",
                "",
                f"- contract: {mode_block.get('agent_contract_ko')}",
                f"- upgrade: `{mode_block.get('session_upgrade')}`",
            ]
            if mode_block.get("pipeline_steps"):
                md_lines.append("- pipeline:")
                for step in mode_block["pipeline_steps"]:
                    md_lines.append(f"  - `{step}`")
            if mode_block.get("artifact_pointers"):
                md_lines.append("- artifacts:")
                for p in mode_block["artifact_pointers"]:
                    md_lines.append(f"  - `{p}`")
        nl_sync = briefing.get("nl_ltm_sync") or {}
        if nl_sync:
            md_lines.append(
                f"- NL 지휘부 sync: push **{nl_sync.get('push_ok')}/{int(nl_sync.get('push_ok') or 0) + int(nl_sync.get('push_fail') or 0)}** "
                f"@ `{nl_sync.get('generated_at_utc')}` · repro: `{nl_sync.get('repro_push')}`"
            )
        md_lines.append("")
    mg = resume.get("mistake_guardrails") or {}
    if mg.get("lines") or mg.get("yaml"):
        md_lines += [
            "## [MISTAKE GUARDRAIL] · JEMA OS kernel ([HYPO])",
            "",
            f"- registry: `{mg.get('registry_path')}` · lane: `{mg.get('lane')}` · format: `{mg.get('format', 'md')}`",
            "",
        ]
        yaml_text = str(mg.get("yaml") or "").strip()
        gf = str(mg.get("format") or "md")
        if yaml_text and gf in ("yaml", "both", "yaml+md"):
            md_lines += ["```yaml", yaml_text, "```", ""]
        if gf in ("md", "both", "yaml+md"):
            for line in mg.get("lines") or []:
                md_lines.append(line if line.startswith("-") else f"- {line}")
            md_lines.append("")
    if pin_freshness_report:
        summary = pin_freshness_report.get("advisory_summary") or {}
        md_lines += [
            "## Pin Freshness Advisory ([HYPO] · P0.3)",
            "",
            f"- stale_pins: `{summary.get('stale_pin_count', 0)}` · "
            f"checkpoint_contradictions: `{summary.get('contradiction_count', 0)}` · "
            f"l0_l2_claim_gaps: `{summary.get('l0_l2_claim_gap_count', 0)}` · "
            f"artifact: `docs/final/artifacts/mkm_resume_pin_freshness_v1_latest.json`",
            "",
        ]
        if pin_l0_l2_gaps:
            md_lines += [
                "> **WARN L0↔L2:** essence claims PASS/DONE but L2 artifact/exit evidence missing "
                "(must_keep alone is not enough).",
                "",
            ]
            for gap in pin_l0_l2_gaps[:5]:
                md_lines.append(
                    f"- **l0_l2_claim_gap** (`{gap.get('gap_reason')}`): "
                    f"`{gap.get('node_id')}` · file=`{gap.get('file_path') or '(none)'}`"
                )
            md_lines.append("")
        for hit in pin_contradictions[:3]:
            md_lines.append(
                f"- **contradicts_prior_checkpoint** ({hit.get('collision_reason')}): "
                f"`{hit.get('newer_stamp_utc')}` vs `{hit.get('older_stamp_utc')}`"
            )
        if pin_contradictions:
            md_lines.append("")
    where_used = resume.get("where_used") or {}
    if where_used.get("topic"):
        paths = ", ".join(f"`{p}`" for p in (where_used.get("ssot_paths") or [])[:8])
        md_lines += [
            "## Where-used SSOT ([HYPO])",
            "",
            f"- topic: `{where_used.get('topic')}` · coverage_ok: `{where_used.get('coverage_ok')}` · "
            f"axes: `{where_used.get('axes_hit')}/{where_used.get('axes_required')}`",
            f"- registry: `{where_used.get('registry')}`",
            f"- ssot_paths: {paths or '`(none hit)`'}",
            f"- reproduce: `{where_used.get('reproduce')}`",
            "",
        ]
    if ops_pins:
        md_lines += ["## Ops Memory Pins ([HYPO])", ""]
        for pin in ops_pins:
            tags = ", ".join(f"`{t}`" for t in pin.get("must_keep_tags") or [])
            stale_note = ""
            if pin.get("stale_advisory"):
                stale_note = (
                    f" · **stale_advisory** age={pin.get('age_days')}d"
                    f">max={pin.get('max_age_days')}d"
                )
            md_lines.append(
                f"- **{pin['node_id']}** — {pin.get('essence')} · must_keep: {tags}{stale_note}"
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

    logos_wiring = resume.get("logos_theory_wiring")
    if logos_wiring:
        md_lines += [
            "## Logos Theory→Implementation Wiring (re-invention guard)",
            "",
            f"- registry: `{logos_wiring.get('registry')}`",
            f"- verify: `{logos_wiring.get('verify_command')}`",
            f"- rule: {logos_wiring.get('agent_rule_ko')}",
            f"- edge_ids: {', '.join(f'`{e}`' for e in logos_wiring.get('edge_ids') or [])}",
            "",
        ]

    module_lane = resume.get("oracle_module_lane")
    if module_lane:
        md_lines += [
            "## Oracle Module Lane (Tier-2 prep · read-only cap)",
            "",
            f"- cursor_rule: `{module_lane.get('cursor_rule')}`",
            f"- tier1_ready: `{module_lane.get('tier1_module_ssot_ready')}` · tier2_prep: `{module_lane.get('tier2_prep_ready')}`",
            f"- resonance_cap (read-only): `{module_lane.get('resonance_cap_read_only')}` · HD: `{module_lane.get('hd_mission_version')}`",
            f"- observability_pass: `{module_lane.get('observation_pass')}`",
            f"- module edges: {', '.join(f'`{e}`' for e in module_lane.get('module_wiring_edge_ids') or [])}",
            f"- weekly: `{module_lane.get('weekly_routine')}`",
            "",
        ]

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
