#!/usr/bin/env python3
"""Phase 11-P: Tier0 prompt sync + NL full pack + pytest closure [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11p_closure_chain_v1_latest.json"
PUSH_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
PACK_MANIFEST = ROOT / "reports/notebooklm_universal_root_research_pack_v1_latest.json"
PROMPT = ROOT / "docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _regenerate_args(manifest: dict) -> None:
    pack = ROOT / str(manifest.get("pack_dir") or "reports/notebooklm_universal_root_research_pack_v1")
    out_dir = ROOT / "reports/nl_mcp_payload/universal_root_research_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in manifest.get("entries") or []:
        if not entry.get("copied"):
            continue
        src = pack / str(entry["pack_name"])
        body = src.read_text(encoding="utf-8")
        title = "MKM_UR_FULL_" + str(entry["pack_name"]).replace("docs__", "").replace("reports__", "")[:90]
        args = {
            "type": "text",
            "content": body,
            "title": title,
            "notebook_id": "14-universal-lexicon-dr",
        }
        (out_dir / f"{entry['pack_name']}.add_source.json").write_text(
            json.dumps(args, ensure_ascii=False),
            encoding="utf-8",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full-push-results", type=Path, default=None)
    ap.add_argument("--skip-push", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(_run("build_nl_research_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))
    pack_doc = _read_json(PACK_MANIFEST)
    _regenerate_args(pack_doc)

    prompt_ok = PROMPT.is_file() and "500-pair, raw_latin" in PROMPT.read_text(encoding="utf-8")
    steps.append({"label": "tier0_prompt_baseline_sync", "ok": prompt_ok, "path": str(PROMPT)})

    if args.full_push_results:
        steps.append(
            _run(
                "record_full_cursor_mcp_push",
                [
                    PY,
                    "scripts/push_notebooklm_universal_root_full_cursor_mcp_v1.py",
                    "--record-results",
                    str(args.full_push_results),
                ],
            )
        )
    elif not args.skip_push:
        steps.append(_run("push_nl_research_pack_nlm", [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_phase11o_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_run_logos_graphrag_phase11o_nl_sandbox_sync_chain_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    push_doc = _read_json(PUSH_OUT)
    push_ok = bool(push_doc.get("all_ok")) if not args.skip_push else True
    all_ok = (
        all(s.get("ok") for s in steps if isinstance(s, dict))
        and bool(pack_doc.get("file_count"))
        and prompt_ok
        and push_ok
    )

    report = {
        "schema": "logos_graphrag_phase11p_closure_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "tier0_prompt_synced": prompt_ok,
        "pack_file_count": pack_doc.get("file_count"),
        "nl_full_push_all_ok": push_doc.get("all_ok"),
        "nl_full_push_ok_count": push_doc.get("ok_count"),
        "nl_full_content": push_doc.get("full_content"),
        "gate_spec_phase": _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
        .get("baseline_observed", {})
        .get("phase"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11p_closure_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out), "push_ok_count": push_doc.get("ok_count")}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
