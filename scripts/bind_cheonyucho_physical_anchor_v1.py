#!/usr/bin/env python3
"""Bind physical scan or commander paste to cheonyucho probe (no auto [CANON])."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
DEFAULT_PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
DEFAULT_ANCHOR = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_v1.json"

HANJA_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
CHEONYU_MARKERS = ("闡幽抄", "闡幽", "천유초")
WRONG_HANJA_MARKERS = ("天有初",)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(raw: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", raw.strip(), flags=re.UNICODE)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return (slug or "PASTE")[:64]


def validate_transcript(text: str) -> dict:
    stripped = text.strip()
    chars = [c for c in stripped if not c.isspace()]
    hanja = HANJA_RE.findall(stripped)
    hanja_count = len(hanja)
    total = len(chars) or 1
    ratio = hanja_count / total
    markers = [m for m in CHEONYU_MARKERS if m in stripped]
    wrong = [m for m in WRONG_HANJA_MARKERS if m in stripped]
    runs = [len(m.group()) for m in re.finditer(r"[\u4e00-\u9fff\u3400-\u4dbf]+", stripped)]
    warnings: list[str] = []
    if len(stripped) < 80:
        warnings.append("transcript_short_under_80_chars")
    if len(stripped) >= 80 and ratio < 0.08:
        warnings.append("low_hanja_ratio")
    if not markers:
        warnings.append("no_cheonyucho_marker")
    if wrong and "闡幽" not in stripped:
        warnings.append("wrong_hanja_tianyou_detected_use_闡幽抄")
    if runs and max(runs) < 4 and hanja_count >= 4:
        warnings.append("short_hanja_runs_only_may_be_index_not_body")
    return {
        "char_count": len(stripped),
        "hanja_count": hanja_count,
        "hanja_ratio": round(ratio, 4),
        "longest_hanja_run": max(runs) if runs else 0,
        "markers_found": markers,
        "wrong_hanja_found": wrong,
        "warnings": warnings,
        "accept_paste": len(stripped) >= 20,
    }


def load_paste_text(paste_file: Path | None, transcript: str | None) -> tuple[str, str]:
    if paste_file is not None:
        if not paste_file.is_file():
            raise FileNotFoundError(f"missing paste file: {paste_file}")
        text = paste_file.read_text(encoding="utf-8", errors="replace")
        return text, str(paste_file.resolve())
    if transcript is not None and transcript.strip():
        return transcript, "inline_transcript"
    raise ValueError("no paste content")


def write_paste_proxy(slug: str, text: str, anchor_meta: dict) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    proxy = RAW / f"CHEONYUCHO_PHYSICAL_{slug}_nl_proxy.md"
    validation = anchor_meta.get("transcript_validation") or {}
    lines = [
        f"# NL Proxy — CHEONYUCHO_PHYSICAL_{slug}",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD`",
        "**ingest:** `scripts/bind_cheonyucho_physical_anchor_v1.py`",
        f"**isbn:** {anchor_meta.get('isbn') or '—'}",
        f"**call_no:** {anchor_meta.get('library_call_no') or '—'}",
        f"**page:** {anchor_meta.get('page') or '—'}",
        f"**transcript_sha256:** `{anchor_meta.get('transcript_sha256', '')}`",
        "**tier:** T0_candidate_paste · human gate required for `[CANON]`",
        "",
        "## MKM ingest flags",
        "",
        "- `physical_verified`: only if commander passes `--set-physical-verified`",
        "- `hanja_canon_status`: stays `not_acquired` from this script",
        "- validation warnings are advisory only",
        "",
        "## Validation",
        "",
        "```json",
        json.dumps(validation, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Transcript (commander / HTR paste)",
        "",
        text.strip(),
        "",
    ]
    proxy.write_text("\n".join(lines), encoding="utf-8")
    return proxy


def run_fragment_mine() -> dict:
    cmd = [sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (proc.stdout or proc.stderr or "")[-400:]
    return {"exit_code": proc.returncode, "tail": tail}


def patch_probe(probe_path: Path, anchor: dict, *, set_physical_verified: bool) -> None:
    if not probe_path.is_file():
        return
    probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
    probe["physical_anchor"] = {
        k: anchor[k]
        for k in (
            "scan_sha256",
            "transcript_sha256",
            "isbn",
            "library_call_no",
            "page",
            "scan_path",
            "paste_proxy_path",
            "jsg_data_id",
        )
        if anchor.get(k)
    }
    probe["last_run_physical"] = {
        "bound_at_utc": anchor["updated_at_utc"],
        "artifact": anchor.get("artifact_rel"),
        "transcript_validation_warnings": (anchor.get("transcript_validation") or {}).get("warnings", []),
    }
    if set_physical_verified:
        probe["physical_verified"] = True
        anchor["physical_verified"] = True
    probe["updated_at_utc"] = _utc()
    probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", type=Path, default=None, help="Photo or PDF of physical page")
    ap.add_argument("--paste-file", type=Path, default=None, help="UTF-8 transcript / index paste")
    ap.add_argument("--transcript", default="", help="Inline paste (prefer --paste-file for long text)")
    ap.add_argument("--slug", default="", help="Proxy slug (default: call-no or timestamp)")
    ap.add_argument("--isbn", default="", help="e.g. 9788992971706")
    ap.add_argument("--call-no", default="", help="e.g. NLK 199.1-이617ㄱ")
    ap.add_argument("--page", default="", help="e.g. p.344 or index")
    ap.add_argument("--jsg-data-id", default="", help="장서각 dataId when applicable")
    ap.add_argument("--note", default="", help="human note")
    ap.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--anchor-out", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument(
        "--run-fragment-mine",
        action="store_true",
        help="After paste proxy write, run run_cheonyucho_fragment_mine_v1.py",
    )
    ap.add_argument(
        "--set-physical-verified",
        action="store_true",
        help="Human gate only: set probe physical_verified true",
    )
    ap.add_argument(
        "--no-patch-probe",
        action="store_true",
        help="Write proxy/anchor only; do not mutate acquisition probe",
    )
    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()

    has_scan = args.scan is not None
    has_paste = args.paste_file is not None or bool(args.transcript.strip())
    if not has_scan and not has_paste:
        print(json.dumps({"ok": False, "error": "provide --scan and/or --paste-file / --transcript"}))
        return 1

    if has_scan and not args.scan.is_file():
        print(json.dumps({"ok": False, "error": f"missing scan: {args.scan}"}))
        return 1

    slug = _slugify(args.slug or args.call_no or args.isbn or f"PASTE_{_utc()[:10]}")

    anchor: dict = {
        "schema": "cheonyucho_physical_anchor_v1",
        "version": "1.1.0",
        "updated_at_utc": _utc(),
        "send_gate": "HOLD",
        "hanja_canon_status": "not_acquired",
        "isbn": args.isbn or None,
        "library_call_no": args.call_no or None,
        "page": args.page or None,
        "jsg_data_id": args.jsg_data_id or None,
        "note": args.note or None,
        "scan_path": None,
        "scan_sha256": None,
        "transcript_sha256": None,
        "paste_proxy_path": None,
        "transcript_validation": None,
    }

    if has_scan:
        anchor["scan_path"] = str(args.scan.resolve())
        anchor["scan_sha256"] = _sha256_file(args.scan)

    mine_result: dict | None = None
    if has_paste:
        try:
            text, paste_src = load_paste_text(args.paste_file, args.transcript or None)
        except (FileNotFoundError, ValueError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
            return 1
        validation = validate_transcript(text)
        if not validation["accept_paste"]:
            print(json.dumps({"ok": False, "error": "paste too short (<20 chars)", "validation": validation}))
            return 1
        digest = _sha256_bytes(text.encode("utf-8"))
        anchor["transcript_sha256"] = digest
        anchor["transcript_validation"] = validation
        anchor["paste_source"] = paste_src
        proxy = write_paste_proxy(slug, text, anchor)
        rel_proxy = str(proxy.relative_to(ROOT)).replace("\\", "/")
        anchor["paste_proxy_path"] = rel_proxy
        if args.run_fragment_mine:
            mine_result = run_fragment_mine()
            if mine_result["exit_code"] != 0:
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "fragment_mine_failed",
                            "mine": mine_result,
                            "paste_proxy": rel_proxy,
                        },
                        ensure_ascii=False,
                    )
                )
                return 1

    anchor_rel = _rel_path(args.anchor_out)
    anchor["artifact_rel"] = anchor_rel
    args.anchor_out.parent.mkdir(parents=True, exist_ok=True)
    args.anchor_out.write_text(json.dumps(anchor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_patch_probe:
        patch_probe(args.probe, anchor, set_physical_verified=args.set_physical_verified)
        if args.set_physical_verified:
            args.anchor_out.write_text(json.dumps(anchor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = {
        "ok": True,
        "artifact": str(args.anchor_out),
        "scan_sha256": anchor.get("scan_sha256"),
        "transcript_sha256": anchor.get("transcript_sha256"),
        "paste_proxy_path": anchor.get("paste_proxy_path"),
        "warnings": (anchor.get("transcript_validation") or {}).get("warnings", []),
        "hanja_canon_status": "not_acquired",
        "fragment_mine": mine_result,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
