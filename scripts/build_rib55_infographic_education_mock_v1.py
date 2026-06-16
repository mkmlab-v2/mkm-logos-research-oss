#!/usr/bin/env python3
"""[HYPO] Build elementary health-education HTML mock from rib55 manifest (no external send)."""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT = ROOT / "reports/demo/rib55_infographic_education_mock_v1.html"
REPORT = ROOT / "reports/rib55_infographic_education_mock_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_img_path(entry: dict, workspace_root: Path) -> str:
    ver = entry.get("verification") or {}
    last_out = ver.get("last_output")
    if last_out:
        return Path(last_out).as_posix()
    entry_id = entry.get("entry_id", "pilot")
    return f"docs/final/artifacts/rib55_overlay_{entry_id}_latest.png"


def render_html(entry: dict, *, manifest: dict, img_href: str) -> str:
    inf = entry.get("infographic_field_v1") or {}
    pts = (entry.get("anatomical_reference_points_v1") or {}).get("points") or []
    source = entry.get("source") or {}
    headline = html.escape(str(inf.get("headline_ko") or "갈비뼈 교육용 그림"))
    subtitle = html.escape(str(inf.get("subtitle_ko") or ""))
    footer = html.escape(str(inf.get("footer_ko") or "[교육용 · 비진단]"))
    system_label = html.escape(str(inf.get("system_label") or "rib sweep — [HYPO]"))
    caption = html.escape(str(entry.get("caption_ko") or ""))
    attr = html.escape(str(source.get("attribution_text") or ""))

    legend_rows = []
    for p in sorted(pts, key=lambda x: str(x.get("infographic_id"))):
        lid = html.escape(str(p.get("infographic_id", "")))
        label = html.escape(str(p.get("label_ko", "")))
        defn = html.escape(str(p.get("definition_ko", "")))
        legend_rows.append(
            f"<li><strong>{lid}</strong> — {label}<br><span class=\"muted\">{defn}</span></li>"
        )
    legend_html = "\n".join(legend_rows)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex,nofollow">
<title>{headline} [HYPO · 내부]</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root {{
  --bg: #fff8f5;
  --text: #1a1a1a;
  --muted: #5c5c5c;
  --accent: #e11d48;
  --line: #f0d4d9;
  --card: #ffffff;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "Pretendard Variable", Pretendard, system-ui, sans-serif;
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
}}
.badge {{
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: 999px;
  background: #fef2f2;
  color: var(--accent);
  border: 1px solid var(--line);
  margin-bottom: 12px;
}}
h1 {{ font-size: 1.45rem; margin: 0 0 8px; letter-spacing: -0.02em; }}
.sub {{ color: var(--muted); font-size: 1.05rem; margin-bottom: 20px; }}
figure {{
  margin: 0 0 20px;
  padding: 12px;
  background: var(--card);
  border: 2px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(225,29,72,0.06);
}}
figure img {{ width: 100%; height: auto; border-radius: 10px; display: block; }}
figcaption {{ font-size: 12px; color: var(--muted); margin-top: 10px; }}
section {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 16px;
}}
section h2 {{ font-size: 1rem; margin: 0 0 10px; color: var(--accent); }}
ol {{ margin: 0; padding-left: 1.2rem; }}
ol li {{ margin-bottom: 10px; }}
.muted {{ color: var(--muted); font-size: 0.92rem; }}
.footer {{
  font-size: 12px;
  color: var(--muted);
  border-top: 1px dashed var(--line);
  padding-top: 14px;
  margin-top: 8px;
}}
</style>
</head>
<body>
<span class="badge">research_only · send_gate HOLD · 내부 미리보기</span>
<h1>{headline}</h1>
<p class="sub">{subtitle}</p>
<figure>
  <img src="{html.escape(img_href)}" alt="갈비뼈 교육용 오버레이 개념도">
  <figcaption>{system_label} · {caption}</figcaption>
</figure>
<section>
  <h2>세 점으로 보는 갈비뼈 방향 (교육용)</h2>
  <ol>
{legend_html}
  </ol>
  <p class="muted">숫자 각도·임상 진단·하늑각(ISA)과 혼동하지 마세요. 이 그림은 9번 늑골 측면 개념도입니다.</p>
</section>
<p class="footer">{footer}<br>{attr}</p>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--entry-id", default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.manifest.is_file():
        raise SystemExit(f"missing manifest: {args.manifest}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = manifest.get("entries") or []
    if not entries:
        raise SystemExit("manifest has no entries")

    entry = entries[0]
    if args.entry_id:
        entry = next((e for e in entries if e.get("entry_id") == args.entry_id), None)
        if not entry:
            raise SystemExit(f"entry_id not found: {args.entry_id}")

    ver = manifest.get("verification") or {}
    img_rel = ver.get("last_output") or _rel_img_path(entry, ROOT)
    img_path = ROOT / img_rel
    if not img_path.is_file():
        alt = ROOT / f"docs/final/artifacts/rib55_overlay_{entry.get('entry_id')}_latest.png"
        img_rel = alt.relative_to(ROOT).as_posix() if alt.is_file() else img_rel

    out_html = render_html(entry, manifest=manifest, img_href="../../" + Path(img_rel).as_posix())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_html, encoding="utf-8")

    report = {
        "schema": "rib55_infographic_education_mock_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "entry_id": entry.get("entry_id"),
        "out_html": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "image_href": img_rel,
        "ok": True,
        "reproduce": "py scripts/build_rib55_infographic_education_mock_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
