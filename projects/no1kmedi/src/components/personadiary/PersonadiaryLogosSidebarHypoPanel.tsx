"use client";

import { useCallback, useRef, useState } from "react";
import {
  fetchPersonadiaryLogosSidebarForOps,
  formatLogosSidebarHitDetail,
  formatLogosSidebarHitTitle,
  type PersonadiaryLogosSidebarResolvedV1,
} from "@/lib/personadiaryLogosSidebarHypoV1";
import type { PersonadiaryMobileOpsV1 } from "@/lib/personadiaryMobileOpsV1";

const HIT_TYPE_LABEL: Record<string, string> = {
  logos_ann_lite: "구절",
  graphrag_motif: "모티프",
  concept_bridge: "개념 브릿지",
};

type Props = {
  ops: PersonadiaryMobileOpsV1;
};

export function PersonadiaryLogosSidebarHypoPanel({ ops }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<PersonadiaryLogosSidebarResolvedV1 | null>(null);
  const loadedRef = useRef(false);

  const loadSidebar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchPersonadiaryLogosSidebarForOps(ops);
      setResolved(payload);
      loadedRef.current = true;
    } catch {
      setError("참조 지도를 불러오지 못했습니다 — public/data 동기화를 확인하세요.");
      setResolved(null);
    } finally {
      setLoading(false);
    }
  }, [ops]);

  return (
    <section
      className="pd-ops-block pd-logos-sidebar-hypo-v1"
      aria-labelledby="pd-logos-sidebar-title"
      data-contract="logos_sidebar_non_gating_v1"
    >
      <div className="pd-premium-section-inner pd-glass pd-ops-card">
        <details
          className="pd-ops-disclosure pd-logos-sidebar-details"
          onToggle={(e) => {
            const el = e.currentTarget;
            if (el.open && !loadedRef.current && !loading) void loadSidebar();
          }}
        >
          <summary id="pd-logos-sidebar-title" className="pd-logos-sidebar-summary">
            Logos 참조 지도 <span className="pd-ops-hypo-tag">[NON_GATING · HYPO]</span>
          </summary>
          <p className="pd-ops-muted">
            로컬 북극성·일기 텍스트로 후보 재선별 · 은유·거시 서사 영감만 · vote·Track A 없음
          </p>
          {loading && (
            <p className="pd-ops-loading-inline" aria-live="polite">
              참조 지도 불러오는 중…
            </p>
          )}
          {error && <p className="pd-ops-error">{error}</p>}
          {resolved && (
            <>
              <p className="pd-ops-muted pd-logos-sidebar-meta">
                출처: {resolved.diary_text_source === "ops_local" ? "기지 로컬 텍스트" : "기본 아티팩트"}
                {resolved.reranked ? " · 재선별됨" : ""}
                {resolved.diary_text_chars > 0 ? ` · ${resolved.diary_text_chars}자` : ""}
              </p>
              <ul className="pd-ops-week-list pd-logos-sidebar-hits">
                {resolved.hits.map((hit) => (
                  <li key={`${hit.hit_type}-${hit.rank}`} className="pd-logos-sidebar-hit">
                    <span className="pd-logos-sidebar-hit-rank">{hit.rank}</span>
                    <div className="pd-logos-sidebar-hit-body">
                      <span className="pd-logos-sidebar-hit-type">
                        {HIT_TYPE_LABEL[hit.hit_type] ?? hit.hit_type}
                      </span>
                      <strong className="pd-logos-sidebar-hit-title">
                        {formatLogosSidebarHitTitle(hit)}
                      </strong>
                      <p className="pd-ops-muted pd-logos-sidebar-hit-detail">
                        {formatLogosSidebarHitDetail(hit)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="pd-ops-muted pd-logos-sidebar-contract">
                <span className="pd-ops-gate">SEND_GATE: HOLD</span> · prophecy_vote: none ·
                research_only
              </p>
              <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => void loadSidebar()}>
                다시 불러오기
              </button>
            </>
          )}
        </details>
      </div>
    </section>
  );
}
