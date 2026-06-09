#!/usr/bin/env python3
"""NotebookLM minimal portfolio — status dashboard + notebook_ids map emitter.

SSOT: docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json

Outputs:
  reports/notebooklm_portfolio_status_latest.json
  reports/notebooklm_portfolio_status_latest.md
  reports/notebooklm_lens_packs_v1/notebook_ids.json  (--write-notebook-map)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json"
PACK_ROOT = ROOT / "reports/notebooklm_lens_packs_v1"
PACK_INDEX = PACK_ROOT / "index.json"
OUT_JSON = ROOT / "reports/notebooklm_portfolio_status_latest.json"
OUT_MD = ROOT / "reports/notebooklm_portfolio_status_latest.md"
OUT_RENAME = ROOT / "reports/notebooklm_rename_checklist_latest.md"
NOTEBOOK_MAP = PACK_ROOT / "notebook_ids.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pack_stats(lens_pack: str | None) -> dict[str, Any]:
    if not lens_pack:
        return {"status": "n/a", "copied": 0, "missing": 0}
    if not PACK_INDEX.is_file():
        return {"status": "pack_index_missing", "copied": 0, "missing": 0}
    index = _load_json(PACK_INDEX)
    pack = index.get("packs", {}).get(lens_pack, {})
    files = pack.get("files", [])
    copied = sum(1 for f in files if f.get("status") == "copied")
    missing = sum(1 for f in files if f.get("status") == "missing")
    return {"status": "ok" if copied else "empty", "copied": copied, "missing": missing}


def _custom_pack_stats(pack_dir: str | None) -> dict[str, Any]:
    if not pack_dir:
        return {"status": "n/a", "file_count": 0}
    p = ROOT / pack_dir.replace("\\", "/")
    if not p.is_dir():
        return {"status": "missing_dir", "file_count": 0}
    files = [f for f in p.rglob("*") if f.is_file()]
    return {"status": "ok", "file_count": len(files)}


def _live_source_count(notebook_id: str | None, *, skip_live: bool) -> int | None:
    if skip_live or not notebook_id:
        return None
    try:
        raw = subprocess.check_output(
            ["nlm", "source", "list", notebook_id],
            text=True,
            encoding="utf-8-sig",
            stderr=subprocess.DEVNULL,
            timeout=45,
        )
        if not raw.strip():
            return None
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return len(parsed)
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def _ui_sources_display(live: int | None, approx: Any) -> str:
    if live is not None:
        return str(live)
    if approx is not None:
        return f"~{approx}"
    return "?"


def _action_for_notebook(nb: dict[str, Any], pack: dict[str, Any]) -> str:
    status = nb.get("status", "")
    uuid = nb.get("uuid")
    if status == "archive_read_only":
        return "질의 금지 · 아카이브 유지"
    if not uuid:
        return f"Google NL에서 '{nb.get('canonical_name')}' 생성 → uuid 기록"
    if pack.get("status") == "pack_index_missing":
        return "먼저: py scripts/build_notebooklm_lens_source_packs_v1.py"
    if pack.get("missing", 0) > 0:
        return f"팩 missing {pack['missing']}건 — 레포 경로 확인 후 재빌드"
    if nb.get("source_budget_action") == "prune_below_80":
        return "소스 ~80 이하로 prune (notebooklm_06_source_cleanup_guide)"
    if status in ("active_daily", "active_weekly") and nb.get("lens_pack"):
        return "Push-NotebooklmLensPacks_v1.ps1 -DryRun 후 push"
    if status == "active_on_demand" and not uuid:
        return "샌드박스 노트 생성 · 시드 템플릿 붙여넣기"
    return "정상 — ask_question 시 notebook_id 고정"


def build_status(write_notebook_map: bool, *, skip_live_counts: bool = False) -> int:
    if not PORTFOLIO_PATH.is_file():
        print(f"MISSING: {PORTFOLIO_PATH}", file=sys.stderr)
        return 1

    portfolio = _load_json(PORTFOLIO_PATH)
    stamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []

    lens_map: dict[str, str] = {}

    notebook_list = sorted(
        portfolio.get("notebooks", []),
        key=lambda n: (n.get("seq") is None, n.get("seq") or 999),
    )
    for nb in notebook_list:
        lens_pack = nb.get("lens_pack")
        if lens_pack:
            pack = _pack_stats(lens_pack)
        else:
            pack = _custom_pack_stats(nb.get("pack_dir"))

        action = _action_for_notebook(nb, pack if lens_pack else {"status": pack.get("status")})
        live_count = _live_source_count(nb.get("uuid"), skip_live=skip_live_counts)
        row = {
            "key": nb.get("key"),
            "canonical_name": nb.get("canonical_name"),
            "legacy_name": nb.get("legacy_name"),
            "status": nb.get("status"),
            "tier": nb.get("tier"),
            "uuid": nb.get("uuid"),
            "lens_pack": lens_pack,
            "source_budget_max": nb.get("source_budget_max"),
            "ui_sources_approx": nb.get("ui_sources_approx"),
            "ui_sources_live": live_count,
            "when_to_use": nb.get("when_to_use"),
            "pack": pack,
            "next_action": action,
        }
        rows.append(row)

        if nb.get("status", "").startswith("active") and not nb.get("uuid"):
            blockers.append(f"{nb.get('key')}: UUID 미할당 — {nb.get('canonical_name')}")

        if lens_pack and nb.get("uuid") and nb.get("status") not in (
            "archive_read_only",
            "create_recommended",
        ):
            lens_map[lens_pack] = nb["uuid"]

    payload = {
        "schema": "notebooklm_portfolio_status_v1",
        "version": "1.0.0",
        "generated_at_utc": stamp,
        "portfolio_path": str(PORTFOLIO_PATH.relative_to(ROOT)).replace("\\", "/"),
        "active_count": sum(1 for r in rows if str(r.get("status", "")).startswith("active")),
        "blockers": blockers,
        "notebooks": rows,
        "deprecated_count": len(portfolio.get("deprecated", [])),
        "on_demand_lenses": portfolio.get("on_demand_lenses", []),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tiers = portfolio.get("usage_tiers", {})
    lines = [
        "# NotebookLM 미니멀 포트폴리오 — 운영 보드",
        "",
        f"생성: `{stamp}` · SSOT: `docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json`",
        "",
        "## 매일 pin (홈 화면에서 이 2개만)",
        "",
        "| key | Google 제목 | 소스(UI) | 다음 1타 |",
        "|-----|-------------|----------|----------|",
    ]
    pin_keys = set(tiers.get("pin_daily", []))
    row_by_key = {r["key"]: r for r in rows}
    for pk in tiers.get("pin_daily", []):
        r = row_by_key.get(pk)
        if not r:
            continue
        ui = _ui_sources_display(r.get("ui_sources_live"), r.get("ui_sources_approx"))
        lines.append(
            f"| {r['key']} | `{r['canonical_name']}` | {ui} | {r.get('next_action', '')} |"
        )

    lines.extend(
        [
            "",
            "## 주간 · 프로젝트 · 필요 시",
            "",
            "| key | 제목 | status | 소스(UI) |",
            "|-----|------|--------|----------|",
        ]
    )
    show_statuses = {
        "active_weekly",
        "active_project",
        "active_on_demand",
        "observation_only",
        "create_recommended",
    }
    for r in rows:
        if r["key"] in pin_keys or r.get("status") == "archive_read_only":
            continue
        if r.get("status") not in show_statuses:
            continue
        ui = _ui_sources_display(r.get("ui_sources_live"), r.get("ui_sources_approx"))
        lines.append(
            f"| {r['key']} | `{r['canonical_name']}` | {r.get('status')} | {ui} |"
        )

    if blockers:
        lines.extend(["", "## 막힘", ""])
        for b in blockers:
            lines.append(f"- {b}")

    lines.extend(
        [
            "",
            "## 아카이브·금지 (질의하지 말 것)",
            "",
        ]
    )
    for d in portfolio.get("deprecated", []):
        lines.append(
            f"- `{d.get('was')}` (`{d.get('uuid', '')[:8]}…`) → "
            f"{d.get('superseded_by')} · **{d.get('action')}**"
        )

    rename_rows = [
        r
        for r in rows
        if r.get("legacy_name") and r.get("legacy_name") != r.get("canonical_name") and r.get("uuid")
    ]
    if rename_rows:
        lines.extend(
            [
                "",
                "## Google NL 제목 정리 (복붙용)",
                "",
                "노트 제목(연필)에 **새 이름**만 붙여넣기. UUID·소스는 그대로.",
                "",
                "| 지금(긴 이름) | → 바꿀 이름 |",
                "|---------------|-------------|",
            ]
        )
        for r in rename_rows:
            lines.append(f"| `{r['legacy_name']}` | **`{r['canonical_name']}`** |")

    lines.extend(
        [
            "",
            "## 원클릭",
            "",
            "```powershell",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-NotebookLmPortfolioRoutine_v1.ps1",
            "```",
            "",
            "JSON: `reports/notebooklm_portfolio_status_latest.json`",
            "Rename: `reports/notebooklm_rename_checklist_latest.md`",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rename_lines = [
        "# NotebookLM 제목 정리 — 복붙 체크리스트",
        "",
        f"생성: `{stamp}` · 규칙: `NN · 짧은제목` (24자 이내)",
        "",
        "Google NL 홈 → 노트 열기 → **제목 연필** → 아래 **새 이름** 붙여넣기.",
        "",
        "| # | key | 지금 → 새 이름 | UUID |",
        "|---|-----|----------------|------|",
    ]
    for i, r in enumerate(rename_rows, 1):
        uid = r.get("uuid") or ""
        rename_lines.append(
            f"| {i} | {r['key']} | `{r.get('legacy_name')}` → **{r.get('canonical_name')}** | `{uid[:8]}…` |"
        )
    pending_create = [r for r in rows if not r.get("uuid") and r.get("canonical_name")]
    if pending_create:
        rename_lines.extend(["", "## 아직 없음 (새 노트 만들 때)", ""])
        for r in pending_create:
            rename_lines.append(f"- **{r.get('canonical_name')}** (`{r.get('key')}`)")
    rename_lines.extend(
        [
            "",
            "## 한눈에 (정렬 순)",
            "",
        ]
    )
    for nb in notebook_list:
        if nb.get("status") == "archive_read_only":
            continue
        rename_lines.append(f"- `{nb.get('canonical_name')}` — {nb.get('when_to_use', '')}")
    OUT_RENAME.write_text("\n".join(rename_lines) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_RENAME}", file=sys.stderr)

    if write_notebook_map:
        PACK_ROOT.mkdir(parents=True, exist_ok=True)
        map_doc = {
            "schema": "notebooklm_lens_pack_push_map_v1",
            "version": "1.0.0",
            "generated_at_utc": stamp,
            "note": "Auto-generated from NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json — edit portfolio SSOT, not by hand.",
            "lens_notebook_id": lens_map,
        }
        NOTEBOOK_MAP.write_text(json.dumps(map_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {NOTEBOOK_MAP}", file=sys.stderr)

    print(f"WROTE: {OUT_JSON}", file=sys.stderr)
    print(f"WROTE: {OUT_MD}", file=sys.stderr)
    print(
        json.dumps(
            {"exit": "ok", "blockers": len(blockers), "lens_map_keys": list(lens_map)},
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NotebookLM minimal portfolio status")
    ap.add_argument(
        "--write-notebook-map",
        action="store_true",
        help="Emit reports/notebooklm_lens_packs_v1/notebook_ids.json from portfolio UUIDs",
    )
    ap.add_argument(
        "--skip-live-counts",
        action="store_true",
        help="Do not call nlm source list (CI/offline)",
    )
    args = ap.parse_args()
    return build_status(
        write_notebook_map=args.write_notebook_map,
        skip_live_counts=args.skip_live_counts,
    )


if __name__ == "__main__":
    raise SystemExit(main())
