#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LinkedIn B2B draft generator — local JSON queue, Fact-Lock fuel, no auto-publish."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/linkedin_b2b_queue_v1.schema.json"
DEFAULT_QUEUE = ROOT / "data/marketing/linkedin_queue.json"
EXAMPLE_QUEUE = ROOT / "data/marketing/linkedin_queue_v1.example.json"
PUBLIC_COPY = ROOT / "projects/no1kmedi/marketing-site/public-copy.json"
KPI_JSON = ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"
ENTERPRISE_MD = ROOT / "docs/final/artifacts/compression_enterprise_executive_summary_v1.md"
GEMINI_BATCH = ROOT / "scripts/gemini_multimodal_batch.py"
OUT_DIR = ROOT / "reports/marketing/linkedin_drafts"

BANNED_RE = [
    re.compile(p, re.I)
    for p in [
        r"guaranteed\s+returns?",
        r"100%\s*(cure|lossless|restore)",
        r"regulatory\s+risk\s+zero",
        r"neuroscience[- ]proven",
        r"hallucination\s+eliminated",
        r"world[- ]unique\s+os",
        r"always\s+profitable",
        r"신경과학적으로\s+증명",
        r"무손실\s*100%",
        r"환각\s*제거",
    ]
]

DISCLAIMER_EN = (
    "> **[DRAFT]** Not investment advice. No guarantee of returns. "
    "Bench metrics are artifact-bound; re-run before external use. "
    "Not a live trading or clinical trigger."
)
DISCLAIMER_KO = (
    "> **[DRAFT]** 투자 권유·수익 보장 아님. 벤치 수치는 동봉 evidence JSON·아티팩트 경로 기준. "
    "실매매·임상 트리거 아님."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_queue(doc: dict[str, Any]) -> None:
    if doc.get("schema") != "linkedin_b2b_queue_v1":
        raise ValueError("queue schema must be linkedin_b2b_queue_v1")
    if not isinstance(doc.get("items"), list):
        raise ValueError("queue items must be a list")
    try:
        import jsonschema
    except ImportError:
        return
    if SCHEMA_PATH.is_file():
        schema = _load_json(SCHEMA_PATH)
        jsonschema.Draft7Validator(schema).validate(doc)


def _read_text(path: Path, max_chars: int = 120_000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n…[truncated for prompt fuel]\n"
    return text


def _kpi_snippet() -> dict[str, Any]:
    out: dict[str, Any] = {"kpi_path": str(KPI_JSON.relative_to(ROOT)).replace("\\", "/"), "present": False}
    if not KPI_JSON.is_file():
        return out
    doc = _load_json(KPI_JSON)
    active = doc.get("active_kpi") if isinstance(doc.get("active_kpi"), dict) else {}
    out["present"] = True
    out["global_token_saving_rate"] = active.get("global_token_saving_rate")
    out["avg_reconstruction_fidelity_jaccard"] = active.get("avg_reconstruction_fidelity_jaccard")
    out["ultra_saving_policy_ok"] = active.get("ultra_saving_policy_ok")
    out["bench_saving_floor_ok"] = active.get("bench_saving_floor_ok")
    return out


def _scan_banned(text: str) -> list[str]:
    hits: list[str] = []
    for pat in BANNED_RE:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def _assemble_body(item: dict[str, Any], kpi: dict[str, Any], hub: dict[str, Any]) -> str:
    loc = item.get("locale", "en")
    disclaimer = DISCLAIMER_KO if loc == "ko" else DISCLAIMER_EN
    topic = str(item.get("topic", "")).strip()
    hook = str(item.get("hook", "")).strip()
    cta = str(item.get("cta_url", "")).strip()

    lines = [
        f"# LinkedIn B2B post [DRAFT] — {item.get('id')}",
        "",
        disclaimer,
        "",
        f"- **generated_at_utc:** `{_utc_now()}`",
        f"- **mode:** `assemble_only` (no Gemini)",
        f"- **audience:** `{item.get('audience', 'b2b_platform')}`",
        "",
        "## Hook",
        hook or "(set hook in queue item)",
        "",
        "## Topic",
        topic,
        "",
    ]

    if kpi.get("present"):
        rate = kpi.get("global_token_saving_rate")
        jacc = kpi.get("avg_reconstruction_fidelity_jaccard")
        lines.extend(
            [
                "## Artifact-bound metrics (conditional)",
                "",
                f"- Token saving (Track A bench): **{float(rate) * 100:.2f}%**" if isinstance(rate, (int, float)) else "- Token saving: —",
                f"- Avg Jaccard (lexical proxy, not semantic %): **{float(jacc):.3f}**" if isinstance(jacc, (int, float)) else "- Avg Jaccard: —",
                f"- Source: `{kpi.get('kpi_path')}`",
                "",
            ]
        )

    if hub:
        lines.append("## Hub links (from public-copy.json)")
        for key, val in hub.items():
            if isinstance(val, dict) and val.get("href"):
                lines.append(f"- **{key}:** {val.get('label', key)} — {val['href']}")
        lines.append("")

    sources = item.get("source_artifacts") or []
    if sources:
        lines.append("## Source artifacts (read before publish)")
        for rel in sources:
            p = ROOT / str(rel).replace("/", "\\") if "\\" not in str(rel) else ROOT / str(rel)
            rel_s = str(Path(rel)).replace("\\", "/")
            exists = "OK" if p.is_file() else "MISSING"
            lines.append(f"- `{rel_s}` — {exists}")
        lines.append("")

    if cta:
        lines.extend(["## CTA", cta, ""])

    lines.extend(
        [
            "## Human gate",
            "1. Legal / `PUBLIC_FACING` v1.7 review",
            "2. Paste into LinkedIn manually — **no API publish from this script**",
            "",
        ]
    )
    return "\n".join(lines)


def _build_fuel_files(item: dict[str, Any], fuel_dir: Path) -> list[Path]:
    fuel_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    if PUBLIC_COPY.is_file():
        dest = fuel_dir / "public_copy.json"
        dest.write_text(PUBLIC_COPY.read_text(encoding="utf-8"), encoding="utf-8")
        paths.append(dest)

    if ENTERPRISE_MD.is_file():
        dest = fuel_dir / "compression_enterprise_executive_summary_v1.md"
        dest.write_text(_read_text(ENTERPRISE_MD), encoding="utf-8")
        paths.append(dest)

    if KPI_JSON.is_file():
        dest = fuel_dir / "ultra_compression_kpi_summary_latest.json"
        dest.write_text(KPI_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        paths.append(dest)

    for rel in item.get("source_artifacts") or []:
        src = ROOT / str(rel).replace("\\", "/")
        if src.is_file():
            safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(rel).name)[:80]
            dest = fuel_dir / f"source_{safe}"
            dest.write_text(_read_text(src, max_chars=60_000), encoding="utf-8")
            paths.append(dest)

    bundle = fuel_dir / "queue_item.json"
    bundle.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(bundle)
    return paths


def _run_gemini_research(item: dict[str, Any], fuel_paths: list[Path], timeout: int) -> tuple[int, str]:
    loc = item.get("locale", "en")
    lang = "Korean" if loc == "ko" else "English"
    kpi = _kpi_snippet()
    prompt = (
        f"Write a LinkedIn post draft for B2B platform/OEM operators.\n"
        f"Language: {lang}.\n"
        f"Topic: {item.get('topic')}\n"
        f"Opening hook (use or refine): {item.get('hook', '')}\n"
        f"CTA URL (if used): {item.get('cta_url', '')}\n\n"
        "Rules:\n"
        "- Start output with line: **[DRAFT]**\n"
        "- Use ONLY numbers present in the KPI block below or attached MD sources.\n"
        "- Do NOT claim guaranteed returns, 100% lossless, neuroscience proof, or live trading triggers.\n"
        "- Include a one-line disclaimer at the end.\n"
        "- Length: 180-260 words for EN; similar density for KO.\n"
    )
    if kpi.get("present"):
        prompt += (
            "\nKPI (artifact-bound; do not invent other metrics):\n"
            f"- global_token_saving_rate: {kpi.get('global_token_saving_rate')}\n"
            f"- avg_reconstruction_fidelity_jaccard: {kpi.get('avg_reconstruction_fidelity_jaccard')}\n"
            f"- ultra_saving_policy_ok: {kpi.get('ultra_saving_policy_ok')}\n"
            f"- bench_saving_floor_ok: {kpi.get('bench_saving_floor_ok')}\n"
            f"- source: {kpi.get('kpi_path')}\n"
        )
    cmd_base = [
        sys.executable,
        str(GEMINI_BATCH),
        "research",
        "--temperature",
        "0.25",
        "--timeout",
        str(timeout),
    ]
    # Gemini file API rejects application/json attachments (500/400); inline KPI + MD only.
    attach_paths = [fp for fp in fuel_paths if fp.suffix.lower() not in {".json"}]
    last_exit = 1
    last_out = ""
    for attempt in range(3):
        cmd = [*cmd_base, "--prompt", prompt]
        for fp in attach_paths:
            cmd.extend(["--file", str(fp)])
        proc = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        last_exit = proc.returncode
        last_out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if last_exit == 0 and last_out:
            return last_exit, last_out
        if "500 INTERNAL" not in last_out and "503" not in last_out:
            break
        time.sleep(2 * (attempt + 1))
    return last_exit, last_out


def _write_chart(item_id: str) -> Path | None:
    kpi = _kpi_snippet()
    if not kpi.get("present"):
        return None
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    rate = kpi.get("global_token_saving_rate")
    jacc = kpi.get("avg_reconstruction_fidelity_jaccard")
    if not isinstance(rate, (int, float)) or not isinstance(jacc, (int, float)):
        return None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / f"{item_id}_bench_snapshot_{_utc_now()[:10]}.png"
    fig, ax = plt.subplots(figsize=(5, 3))
    labels = ["Token saving", "Jaccard (proxy)"]
    values = [float(rate) * 100, float(jacc) * 100]
    colors = ["#2563eb", "#64748b"]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("% scale (Jaccard shown as % for viz only)")
    ax.set_title("[DRAFT] Track A bench snapshot — artifact-bound")
    ax.set_ylim(0, max(values) * 1.15 + 5)
    fig.text(0.5, 0.02, KPI_JSON.name, ha="center", fontsize=7, color="gray")
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)
    return png


def _evidence_doc(
    item: dict[str, Any],
    mode: str,
    kpi: dict[str, Any],
    fuel_paths: list[Path],
    banned_hits: list[str],
    gemini_exit: int | None,
) -> dict[str, Any]:
    return {
        "schema": "linkedin_b2b_draft_evidence_v1",
        "generated_at_utc": _utc_now(),
        "item_id": item.get("id"),
        "mode": mode,
        "kpi_snippet": kpi,
        "fuel_files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in fuel_paths],
        "public_copy_path": str(PUBLIC_COPY.relative_to(ROOT)).replace("\\", "/"),
        "banned_pattern_hits": banned_hits,
        "gemini_exit_code": gemini_exit,
        "auto_publish": False,
        "policy_refs": [
            "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
        ],
    }


def _process_item(
    item: dict[str, Any],
    *,
    assemble_only: bool,
    use_gemini: bool,
    with_chart: bool,
    gemini_timeout: int,
) -> dict[str, Any]:
    item_id = str(item["id"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fuel_dir = OUT_DIR / f".fuel_{item_id}"
    kpi = _kpi_snippet()
    hub: dict[str, Any] = {}
    if PUBLIC_COPY.is_file():
        pc = _load_json(PUBLIC_COPY)
        hub = pc.get("hub_links") if isinstance(pc.get("hub_links"), dict) else {}

    if assemble_only or not use_gemini:
        body = _assemble_body(item, kpi, hub)
        mode = "assemble_only"
        gemini_exit = None
        fuel_paths: list[Path] = []
    else:
        fuel_paths = _build_fuel_files(item, fuel_dir)
        gemini_exit, body = _run_gemini_research(item, fuel_paths, gemini_timeout)
        mode = "gemini_research"
        if gemini_exit != 0 or not body:
            body = _assemble_body(item, kpi, hub)
            body = (
                f"<!-- Gemini research failed (exit {gemini_exit}); fallback assemble_only -->\n\n"
                + body
            )
            mode = "assemble_fallback"

    banned = _scan_banned(body)
    if banned:
        body += "\n\n<!-- BANNED_PATTERN_WARNING: " + ", ".join(banned) + " -->\n"

    md_path = OUT_DIR / f"{item_id}_{_utc_now()[:10]}_[DRAFT].md"
    md_path.write_text(body, encoding="utf-8")

    chart_path = _write_chart(item_id) if with_chart else None

    evidence = _evidence_doc(item, mode, kpi, fuel_paths, banned, gemini_exit)
    ev_path = OUT_DIR / f"{item_id}_{_utc_now()[:10]}_evidence.json"
    ev_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    draft_paths: dict[str, str] = {
        "markdown": str(md_path.relative_to(ROOT)).replace("\\", "/"),
        "evidence_json": str(ev_path.relative_to(ROOT)).replace("\\", "/"),
    }
    if chart_path:
        draft_paths["chart_png"] = str(chart_path.relative_to(ROOT)).replace("\\", "/")

    return {
        "id": item_id,
        "status": "drafted",
        "drafted_at_utc": _utc_now(),
        "draft_paths": draft_paths,
        "banned_hits": banned,
        "mode": mode,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="LinkedIn B2B draft queue processor (no auto-publish).")
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE, help="Queue JSON path")
    ap.add_argument("--item-id", help="Process single item id")
    ap.add_argument("--assemble-only", action="store_true", help="Template only; no Gemini API")
    ap.add_argument("--gemini", action="store_true", help="Call gemini_multimodal_batch.py research")
    ap.add_argument("--with-chart", action="store_true", help="Emit KPI bar chart PNG if data exists")
    ap.add_argument("--gemini-timeout", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true", help="Validate queue only")
    ap.add_argument("--init-from-example", action="store_true", help="Copy example queue if missing")
    ap.add_argument(
        "--strict-compliance",
        action="store_true",
        help="After draft, run check_linkedin_b2b_draft_copy_v1.py (exit 1 on FAIL)",
    )
    ns = ap.parse_args()

    queue_path: Path = ns.queue
    if ns.init_from_example and not queue_path.is_file() and EXAMPLE_QUEUE.is_file():
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(EXAMPLE_QUEUE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"init: {queue_path}")

    if not queue_path.is_file():
        print(f"queue missing: {queue_path}", file=sys.stderr)
        print(f"hint: py scripts/generate_linkedin_b2b_copy_v1.py --init-from-example", file=sys.stderr)
        return 2

    doc = _load_json(queue_path)
    try:
        _validate_queue(doc)
    except Exception as e:
        print(f"queue validation failed: {e}", file=sys.stderr)
        return 2

    if ns.dry_run:
        n = len(doc.get("items", []))
        print(f"queue ok: {n} item(s) @ {queue_path}")
        return 0

    use_gemini = bool(ns.gemini) and not ns.assemble_only
    if use_gemini and not (_api_key_present()):
        print("GEMINI_API_KEY/GOOGLE_API_KEY unset; use --assemble-only or set key", file=sys.stderr)
        return 2

    items = doc.get("items", [])
    if not isinstance(items, list):
        print("invalid items", file=sys.stderr)
        return 2

    targets = [it for it in items if isinstance(it, dict) and it.get("status") == "pending"]
    if ns.item_id:
        targets = [it for it in items if isinstance(it, dict) and it.get("id") == ns.item_id]
        if not targets:
            print(f"item not found: {ns.item_id}", file=sys.stderr)
            return 2

    if not targets:
        print("no pending items")
        return 0

    by_id = {str(it.get("id")): it for it in items if isinstance(it, dict) and it.get("id")}
    exit_code = 0
    for item in targets:
        try:
            result = _process_item(
                item,
                assemble_only=ns.assemble_only,
                use_gemini=use_gemini,
                with_chart=ns.with_chart,
                gemini_timeout=ns.gemini_timeout,
            )
            item["status"] = result["status"]
            item["drafted_at_utc"] = result["drafted_at_utc"]
            item["draft_paths"] = result["draft_paths"]
            by_id[result["id"]] = item
            print(f"drafted: {result['id']} -> {result['draft_paths'].get('markdown')}")
            if result.get("banned_hits"):
                print(f"  warning: banned pattern hits: {result['banned_hits']}", file=sys.stderr)
                exit_code = 1
        except Exception as e:
            print(f"failed: {item.get('id')}: {e}", file=sys.stderr)
            exit_code = 2

    doc["items"] = [by_id.get(str(it.get("id")), it) for it in items if isinstance(it, dict)]
    doc["updated_at_utc"] = _utc_now()
    queue_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sync_script = ROOT / "scripts/sync_marketing_queue_to_linkedin_v1.py"
    if sync_script.is_file() and exit_code == 0:
        subprocess.run(
            [sys.executable, str(sync_script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    if ns.strict_compliance and exit_code == 0:
        check_script = ROOT / "scripts/check_linkedin_b2b_draft_copy_v1.py"
        proc = subprocess.run(
            [sys.executable, str(check_script), "--drafts-dir", str(OUT_DIR)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(proc.stdout or "", end="")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="")
        if proc.returncode != 0:
            return max(exit_code, proc.returncode)

    return exit_code


def _api_key_present() -> bool:
    import os

    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_STUDIO_API_KEY"))


if __name__ == "__main__":
    raise SystemExit(main())
