#!/usr/bin/env python3
"""Build public showroom Isaiah YouTube reading pack HTML [HYPO].

Reproduce:
  py scripts/build_public_showroom_logos_isaiah_youtube_reading_pack_html_v1.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "public_showroom_logos_isaiah_youtube_reading_pack_v1.html"
)

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>JEMA AI · Isaiah YouTube Reading Pack · Logos</title>
  <style>
    :root {
      --bg: #0a1210;
      --surface: #121a17;
      --border: rgba(255, 255, 255, 0.09);
      --text: #e8f0ed;
      --muted: #8b9d96;
      --accent: #3d9b84;
      --pack1: #8fbc8f;
      --pack2: #3d9b84;
      --pack3: #9eb4d4;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
      font-size: 15px;
      line-height: 1.55;
      color: var(--text);
      background: radial-gradient(900px 480px at 80% -10%, rgba(61, 155, 132, 0.1), transparent 55%), var(--bg);
    }
    .wrap { max-width: 56rem; margin: 0 auto; padding: 1.5rem 1.1rem 2.5rem; }
    header { margin-bottom: 1.25rem; padding-bottom: 0.85rem; border-bottom: 1px solid var(--border); }
    h1 { font-size: 1.2rem; margin: 0 0 0.35rem; font-weight: 650; }
    .lede { margin: 0; font-size: 0.8125rem; color: var(--muted); max-width: 44rem; }
    .badges { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.65rem 0 0; }
    .badge {
      font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em;
      padding: 0.2rem 0.5rem; border-radius: 4px; border: 1px solid var(--border); color: var(--muted);
    }
    .badge-warn { border-color: rgba(61, 155, 132, 0.45); color: var(--accent); }
    .preset-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1rem 0; }
    .preset-btn {
      font-size: 0.75rem; padding: 0.35rem 0.65rem; border-radius: 999px;
      border: 1px solid var(--border); background: var(--surface); color: var(--text);
      cursor: pointer;
    }
    .preset-btn:hover, .preset-btn.active { border-color: var(--accent); color: var(--accent); }
    .pack-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.75rem; }
    .pack-tab {
      font-size: 0.72rem; padding: 0.4rem 0.75rem; border-radius: 8px 8px 0 0;
      border: 1px solid var(--border); border-bottom: none; background: #0e1412; color: var(--muted);
      cursor: pointer;
    }
    .pack-tab.active { background: var(--surface); color: var(--text); border-color: var(--accent); }
    .pack-tab[data-pack="canonical_citations_only"].active { border-top: 2px solid var(--pack1); }
    .pack-tab[data-pack="studio_spine_five_anchors"].active { border-top: 2px solid var(--pack2); }
    .pack-tab[data-pack="chapter_route_sixteen"].active { border-top: 2px solid var(--pack3); }
    .card {
      border: 1px solid var(--border); border-radius: 0 12px 12px 12px;
      background: linear-gradient(180deg, #151c19 0%, var(--surface) 100%);
      padding: 1rem 1.1rem 1.15rem; min-height: 12rem;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
    }
    .card h2 { font-size: 1rem; margin: 0 0 0.35rem; font-weight: 600; }
    .card .summary { font-size: 0.78rem; color: var(--muted); margin: 0 0 0.85rem; }
    .card-body {
      font-size: 0.8125rem; color: #c8d4cf; max-height: 22rem; overflow-y: auto;
      white-space: pre-wrap; word-break: break-word;
    }
    .card-body strong { color: var(--accent); font-weight: 600; }
    .timeline { margin-top: 1.25rem; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); padding: 0.85rem 1rem; }
    .timeline h3 { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); margin: 0 0 0.65rem; }
    .stage { display: grid; grid-template-columns: 2rem 1fr; gap: 0 0.65rem; margin-bottom: 0.75rem; }
    .stage:last-child { margin-bottom: 0; }
    .stage-num {
      width: 1.75rem; height: 1.75rem; border-radius: 50%; border: 1px solid var(--border);
      display: flex; align-items: center; justify-content: center; font-size: 0.7rem; color: var(--accent);
    }
    .stage.active .stage-num { background: rgba(61, 155, 132, 0.15); border-color: var(--accent); }
    .stage.dim { opacity: 0.35; }
    .stage-title { font-size: 0.8125rem; font-weight: 600; margin: 0; }
    .stage-bottleneck { font-size: 0.72rem; color: var(--muted); margin: 0.2rem 0 0; }
    .stage-refs { font-size: 0.65rem; font-family: ui-monospace, monospace; color: #6b7a73; margin-top: 0.25rem; }
    .stage-verdict { font-size: 0.65rem; color: var(--pack3); }
    .meta-line { font-size: 0.68rem; color: var(--muted); margin-top: 1rem; }
    .footer-links { font-size: 0.75rem; margin-top: 1.25rem; }
    .footer-links a { color: var(--accent); text-decoration: none; }
    .footer-links a:hover { text-decoration: underline; }
    #loadErr { color: #f87171; font-size: 0.8125rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <p class="lede" style="text-transform:uppercase;letter-spacing:0.14em;font-size:0.65rem;margin-bottom:0.35rem;">JEMA AI · Track C Showroom · Logos</p>
      <h1>Isaiah YouTube · 16챕터 Reading Pack</h1>
      <p class="lede" id="disclaimerLine">이사야 66장 유튜브 강해 — MKM bridge 3-Pack · 정적 스냅샷</p>
      <div class="badges">
        <span class="badge badge-warn">[HYPO]</span>
        <span class="badge">NON_GATING</span>
        <span class="badge">send_gate HOLD</span>
        <span class="badge">16 chapters</span>
      </div>
    </header>

    <p id="loadStatus" class="meta-line">데이터 로드 중…</p>
    <p id="loadErr" hidden></p>

    <div class="preset-row" id="presetRow" aria-label="Chapter presets"></div>

    <div class="pack-tabs" id="packTabs" role="tablist"></div>
    <article class="card" id="packCard" aria-live="polite">
      <h2 id="cardTitle">—</h2>
      <p class="summary" id="cardSummary">—</p>
      <div class="card-body" id="cardBody"></div>
    </article>

    <section class="timeline" id="timeline" aria-label="Narrative route">
      <h3>16챕터 서사 경로</h3>
      <div id="stageList"></div>
    </section>

    <p class="meta-line" id="metaLine">—</p>

    <p class="footer-links">
      <a id="studioLink" href="https://logos.jema-ai.com/logos-research/studio?q=isaiah_youtube_spine_v1&amp;autorun=1&amp;demo=1" rel="noopener">→ Logos Studio (isaiah_youtube_spine_v1)</a>
      ·
      <a id="qaStudioLink" href="public_showroom_meaning_topology_qa_v2.html?preset=isaiah_youtube_spine_v1">→ Q&amp;A Studio (그래프)</a>
      ·
      <a href="public_showroom_logos_job_reading_pack_v1.html">→ Job Reading Pack</a>
      ·
      <a href="public_showroom_meaning_topology_graph_v1.html">Meaning topology graph</a>
    </p>
  </div>

  <script>
(function () {
  "use strict";
  const SLICE_URL = "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json";
  const PACK_ORDER = ["canonical_citations_only", "studio_spine_five_anchors", "chapter_route_sixteen"];
  const DEFAULT_STUDIO = "https://logos.jema-ai.com/logos-research/studio";

  let doc = null;
  let activePack = PACK_ORDER[0];
  let activePreset = null;
  let stageFilter = null;

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderMdLite(text) {
    return esc(text)
      .replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<span style='color:#9eb4d4'>$1</span>");
  }

  function packById(id) {
    return (doc.reading_packs || []).find(function (p) { return p.pack_id === id; });
  }

  function qaStudioHref(presetId) {
    var pid = presetId || "isaiah_youtube_spine_v1";
    return "public_showroom_meaning_topology_qa_v2.html?preset=" + encodeURIComponent(pid);
  }

  function studioHref(presetId) {
    var pid = presetId || "isaiah_youtube_spine_v1";
    return DEFAULT_STUDIO + "?q=" + encodeURIComponent(pid) + "&autorun=1&demo=1";
  }

  function updateLinks(presetId) {
    var qa = document.getElementById("qaStudioLink");
    var st = document.getElementById("studioLink");
    if (qa) qa.href = qaStudioHref(presetId);
    if (st) st.href = studioHref(presetId);
  }

  function renderPack(packId) {
    activePack = packId;
    const p = packById(packId);
    if (!p) return;
    document.querySelectorAll(".pack-tab").forEach(function (t) {
      t.classList.toggle("active", t.dataset.pack === packId);
    });
    document.getElementById("cardTitle").textContent = p.label_ko || packId;
    document.getElementById("cardSummary").textContent = p.summary_ko || "";
    document.getElementById("cardBody").innerHTML = renderMdLite(p.card_excerpt_ko || "");
    renderStages();
  }

  function renderStages() {
    const box = document.getElementById("stageList");
    box.innerHTML = "";
    const filter = stageFilter;
    (doc.narrative_route_public || []).forEach(function (s) {
      const on = !filter || !filter.size || filter.has(s.stage_id);
      const row = document.createElement("div");
      row.className = "stage" + (on ? " active" : " dim");
      row.innerHTML =
        "<div class='stage-num'>" + esc(String(s.order || "")) + "</div>" +
        "<div><p class='stage-title'>" + esc(s.label_ko || s.stage_id) + "</p>" +
        "<p class='stage-bottleneck'>" + esc(s.bottleneck_ko || "") + "</p>" +
        "<p class='stage-verdict'>MKM: " + esc(s.mkm_verdict || "?") + "</p>" +
        "<p class='stage-refs'>" + esc((s.verse_refs || []).join(" · ")) + "</p></div>";
      box.appendChild(row);
    });
  }

  function renderTabs() {
    const tabs = document.getElementById("packTabs");
    tabs.innerHTML = "";
    PACK_ORDER.forEach(function (id) {
      const p = packById(id);
      if (!p) return;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pack-tab";
      b.dataset.pack = id;
      b.setAttribute("role", "tab");
      b.textContent = p.label_ko.length > 28 ? p.label_ko.slice(0, 26) + "…" : p.label_ko;
      b.title = p.label_ko;
      b.addEventListener("click", function () { renderPack(id); });
      tabs.appendChild(b);
    });
  }

  function applyHighlightPreset(hp) {
    activePreset = hp.preset_id;
    stageFilter = null;
    if (hp.narrative_stage_ids && hp.narrative_stage_ids.length) {
      stageFilter = new Set(hp.narrative_stage_ids);
    }
    updateLinks(hp.preset_id);
    renderStages();
    const packs = hp.pack_ids || [];
    if (packs.length) renderPack(packs[0]);
  }

  function renderPresets() {
    const row = document.getElementById("presetRow");
    row.innerHTML = "";
    (doc.highlight_presets || []).forEach(function (hp) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "preset-btn";
      b.textContent = hp.label_ko;
      b.addEventListener("click", function () {
        document.querySelectorAll(".preset-btn").forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        applyHighlightPreset(hp);
      });
      row.appendChild(b);
    });
  }

  function applyUrlParams() {
    const params = new URLSearchParams(location.search);
    const preset = params.get("preset");
    const pack = params.get("pack");
    if (pack && packById(pack)) renderPack(pack);
    if (preset) {
      const hp = (doc.highlight_presets || []).find(function (h) {
        return h.preset_id === preset || h.preset_id === "isaiah_yt_" + preset;
      });
      if (hp) {
        document.querySelectorAll(".preset-btn").forEach(function (b) {
          if (b.textContent === hp.label_ko) b.classList.add("active");
        });
        applyHighlightPreset(hp);
      } else {
        updateLinks(preset.startsWith("isaiah_") ? preset : "isaiah_yt_" + preset);
        renderStages();
      }
    } else {
      updateLinks(null);
    }
  }

  function boot() {
    fetch(SLICE_URL)
      .then(function (r) {
        if (!r.ok) throw new Error(SLICE_URL + " HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        doc = data;
        if (data.disclaimer && data.disclaimer.note_ko) {
          document.getElementById("disclaimerLine").textContent = data.disclaimer.note_ko;
        }
        var stale = data.stale_after_utc ? (" · stale_after " + data.stale_after_utc) : "";
        document.getElementById("loadStatus").textContent =
          (data.query_ko || data.query_id) + " · packs=" + (data.reading_packs || []).length +
          " · bridge_ok=" + (data.export_gate && data.export_gate.bridge_map_ok) + stale;
        document.getElementById("metaLine").textContent =
          "generated " + (data.generated_at_utc || "?") + " · anchor " + (data.anchor_ref || "?");
        renderTabs();
        renderPresets();
        renderPack(activePack);
        applyUrlParams();
      })
      .catch(function (err) {
        document.getElementById("loadStatus").textContent = "";
        var el = document.getElementById("loadErr");
        el.hidden = false;
        el.textContent = "로드 실패: " + err + " — slice/HTML 빌드 후 새로고침하세요.";
      });
  }

  boot();
})();
  </script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(HTML, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
