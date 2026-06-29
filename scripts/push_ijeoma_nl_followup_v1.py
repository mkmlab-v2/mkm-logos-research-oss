#!/usr/bin/env python3
"""IJEOMA NL follow-up: G-vault secondary (격치고·유고·천유초 proxy) + donguibogam remainder."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
VENDOR = ROOT / "vendor/korean-medicine-texts"
INDEX = ROOT / "reports/km_classics_index_hypo_v1_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_nl_followup_v1.json"
HEADER = (
    "[HYPO] B-track KM classic · clinician_lane_only · not clinical prescription · send_gate HOLD\n\n"
)
CHUNK = 6_000
PREFIX_RESERVE = 220
CAP = 300

SECONDARY_SOURCES: list[tuple[str, Path]] = [
    (
        "[SECONDARY] GEUKCHIGO_YUGO_insight",
        ROOT / "docs/final/IJEOMA_GEUKCHIGO_YUGO_SECONDARY_INSIGHT_2026-03-29.md",
    ),
    (
        "[PAPER_PROXY] GEUKCHI_CHEONYU_layer",
        ROOT / "docs/final/IJEOMA_GEUKCHI_CHEONYU_PAPER_PROXY_LAYER_2026-03-29.md",
    ),
    (
        "[PAPER_PROXY] SCISPACE_sasang_items",
        ROOT / "docs/final/SCISPACE_SASANG_LITERATURE_HELPFUL_ITEMS_2026-03-29.md",
    ),
    (
        "[SECONDARY] KOREAN_MEDICAL_CANON_handoff",
        ROOT / "docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md",
    ),
]

PLACEHOLDER_TITLES = {"IJEOMA_GEUKCHIGO_PLACEHOLDER_v1"}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _notebook_source_count() -> int:
    proc = subprocess.run(
        ["nlm", "notebook", "get", UUID, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return CAP
    payload = json.loads(proc.stdout)
    val = payload.get("value") or payload
    return len(val.get("sources") or [])


def _find_source_ids_by_titles(titles: set[str]) -> list[str]:
    proc = subprocess.run(
        ["nlm", "notebook", "get", UUID, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return []
    payload = json.loads(proc.stdout)
    val = payload.get("value") or payload
    ids: list[str] = []
    for s in val.get("sources") or []:
        if s.get("title") in titles:
            ids.append(s["id"])
    return ids


def _upload_once(title: str, text: str, sleep_s: float) -> dict:
    cmd = ["nlm", "source", "add", UUID, "--text", text, "--title", title[:120], "--wait"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "Added source" in out
    row = {"title": title, "ok": ok, "chars": len(text), "tail": out[-160:]}
    print(json.dumps({"title": title, "ok": ok}, ensure_ascii=False), flush=True)
    if sleep_s > 0:
        time.sleep(sleep_s)
    return row


def _upload(title: str, text: str, sleep_s: float) -> dict:
    if len(text) <= CHUNK:
        return _upload_once(title, text, sleep_s)
    last: dict = {"title": title, "ok": False}
    parts = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    for i, part in enumerate(parts):
        t = title if i == 0 else f"{title}__p{i}"
        last = _upload_once(t, part, sleep_s)
    return last


def _upload_donguibogam_range(start_part: int, max_parts: int, sleep_s: float) -> list[dict]:
    rows: list[dict] = []
    if not INDEX.is_file():
        rows.append({"title": "donguibogam", "ok": False, "error": "missing_index"})
        return rows
    index_doc = json.loads(INDEX.read_text(encoding="utf-8"))
    entry = next((e for e in index_doc.get("entries", []) if e.get("source_id") == "donguibogam"), None)
    if not entry:
        rows.append({"title": "donguibogam", "ok": False, "error": "no_index_entry"})
        return rows
    rel = entry.get("relative_path")
    path = VENDOR / str(rel).replace("/", "\\")
    if not path.is_file():
        rows.append({"title": "donguibogam", "ok": False, "error": f"missing:{path}"})
        return rows
    body = path.read_text(encoding="utf-8", errors="replace")
    chunks = [body[i : i + CHUNK] for i in range(0, len(body), CHUNK)]
    end = min(len(chunks), start_part + max_parts) if max_parts > 0 else len(chunks)
    for idx in range(start_part, end):
        if _notebook_source_count() >= CAP:
            rows.append({"title": f"km_vendor_donguibogam__p{idx}", "ok": False, "error": "cap_reached"})
            break
        part = chunks[idx]
        title = "km_vendor_donguibogam" if idx == 0 else f"km_vendor_donguibogam__p{idx}"
        mini = f"# donguibogam part {idx}/{len(chunks)-1}\n\n"
        payload = HEADER + mini + part
        if len(payload) > CHUNK:
            payload = HEADER + mini + part[: CHUNK - len(HEADER) - len(mini)]
        rows.append(_upload_once(title, payload, sleep_s))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.85)
    parser.add_argument("--donguibogam-start-part", type=int, default=61)
    parser.add_argument("--skip-donguibogam", action="store_true")
    parser.add_argument("--skip-secondary", action="store_true")
    parser.add_argument("--replace-geukchigo-placeholder", action="store_true", default=True)
    parser.add_argument("--no-replace-geukchigo-placeholder", action="store_false", dest="replace_geukchigo_placeholder")
    args = parser.parse_args()

    rows: list[dict] = []
    pre = _notebook_source_count()
    budget = max(0, CAP - pre)

    if args.replace_geukchigo_placeholder:
        ids = _find_source_ids_by_titles(PLACEHOLDER_TITLES)
        if ids:
            proc = subprocess.run(
                ["nlm", "source", "delete", *ids, "--confirm"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
            )
            ok = proc.returncode == 0
            rows.append({"action": "delete_placeholder", "ids": ids, "ok": ok})
            print(json.dumps({"delete_placeholder": ok, "count": len(ids)}, ensure_ascii=False), flush=True)
            if ok:
                budget += len(ids)

    if not args.skip_secondary:
        for title, path in SECONDARY_SOURCES:
            if _notebook_source_count() >= CAP:
                rows.append({"title": title, "ok": False, "error": "cap_reached"})
                continue
            if not path.is_file():
                rows.append({"title": title, "ok": False, "error": f"missing:{path}"})
                continue
            body = HEADER + path.read_text(encoding="utf-8", errors="replace")
            row = _upload(title, body, args.sleep)
            rows.append(row)

    if not args.skip_donguibogam:
        remaining = max(0, CAP - _notebook_source_count())
        if remaining > 0:
            rows.extend(_upload_donguibogam_range(args.donguibogam_start_part, remaining, args.sleep))

    post = _notebook_source_count()
    doc = {
        "schema": "comp_ijeoma_nl_followup_v1",
        "generated_at_utc": _utc(),
        "notebook_uuid": UUID,
        "pre_count": pre,
        "post_count": post,
        "ok": sum(1 for r in rows if r.get("ok")),
        "fail": sum(1 for r in rows if r.get("ok") is False),
        "rows": rows,
        "note": "G-vault secondary replaces GEUKCHIGO placeholder; donguibogam continues part index.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "pre": pre, "post": post}, ensure_ascii=False))
    return 0 if doc["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
