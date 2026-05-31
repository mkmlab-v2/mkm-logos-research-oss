from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    extract_node_from_index,
    top_nodes_by_priority,
    truncate_anchor_slice,
    utc_now_iso,
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


def _load_ops_pins(
    root: Path,
    *,
    top_n: int,
    include_slice: bool,
    slice_max_chars: int,
) -> List[Dict[str, Any]]:
    index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
    if not index_path.is_file():
        return []
    index = _read_json(index_path)
    pins: List[Dict[str, Any]] = []
    for node_id, node in top_nodes_by_priority(index, top_n=top_n):
        pin: Dict[str, Any] = {
            "node_id": node_id,
            "essence": node.get("essence"),
            "must_keep_tags": node.get("must_keep_tags") or [],
            "file_path": node.get("file_path"),
            "line_range": node.get("line_range"),
        }
        if include_slice:
            block = extract_node_from_index(root, node)
            preview, truncated = truncate_anchor_slice(
                block, max_chars=slice_max_chars
            )
            pin["slice_preview"] = preview
            pin["slice_truncated"] = truncated
            pin["slice_max_chars"] = slice_max_chars
        pins.append(pin)
    return pins


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=2)
    ap.add_argument(
        "--include-slice",
        action="store_true",
        help="[HYPO] Include truncated anchor body per pin (Phase 0.5).",
    )
    ap.add_argument(
        "--slice-max-chars",
        type=int,
        default=1200,
        help="Max chars per anchor slice preview (default 1200).",
    )
    args = ap.parse_args()

    if args.slice_max_chars < 64:
        print("FAIL: --slice-max-chars must be >= 64", file=sys.stderr)
        return 1

    root = SCRIPT_ROOT
    art = root / "docs" / "final" / "artifacts"

    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")

    ops_pins = _load_ops_pins(
        root,
        top_n=args.top_n,
        include_slice=args.include_slice,
        slice_max_chars=args.slice_max_chars,
    )
    inject_text = _build_ops_inject_text(ops_pins)

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
            "include_slice": args.include_slice,
            "slice_max_chars": args.slice_max_chars if args.include_slice else None,
            "top_n": args.top_n,
        },
        "quick_refs": {
            "central_memory": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "ops_memory_index": "storage/meta/mkm_ops_memory_index_v1.json",
            "ops_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "ops_dashboard_exec_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md",
            "acceptance_json": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "runbook_checklist_md": "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md",
            "core_prompt_gemini_athena": "docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V1.md",
        },
        "ops_memory_pins": ops_pins,
        "latest_status": {
            "system_status": (dashboard.get("system") or {}).get("status"),
            "promotion_decision": (dashboard.get("system") or {}).get("promotion_decision"),
            "trackc_packet_status": (dashboard.get("trackc") or {}).get("packet_status"),
            "acceptance_status": acceptance.get("status"),
        },
        "resume_commands": [
            "py scripts/build_mkm_ops_memory_index_v1.py",
            "py scripts/build_mkm_chat_resume_pack_v1.py --include-slice",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -IncludeSlice",
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
        f"- include_slice: `{args.include_slice}`",
        f"- system_status: `{resume['latest_status'].get('system_status')}`",
        f"- promotion_decision: `{resume['latest_status'].get('promotion_decision')}`",
        f"- trackc_packet_status: `{resume['latest_status'].get('trackc_packet_status')}`",
        f"- acceptance_status: `{resume['latest_status'].get('acceptance_status')}`",
        "",
    ]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
