"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH,
  type LogosTopologyHubV1,
  isLogosTopologyHubV1,
} from "@/lib/universeHubLogosTopologyV1";

export function HubEvidenceInspectorV3() {
  const pathname = usePathname() ?? "";
  const onLogos = pathname.startsWith("/hub/logos");
  const [topology, setTopology] = useState<LogosTopologyHubV1 | null>(null);

  useEffect(() => {
    if (!onLogos) {
      setTopology(null);
      return;
    }
    let cancelled = false;
    fetch(UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && isLogosTopologyHubV1(data)) {
          setTopology(data);
        }
      })
      .catch(() => {
        if (!cancelled) setTopology(null);
      });
    return () => {
      cancelled = true;
    };
  }, [onLogos]);

  const hubs = topology?.global_centrality_hubs?.slice(0, 3) ?? [];

  return (
    <div className="universe-hub-inspector-inner">
      <p className="universe-hub-inspector-badge" data-testid="hub-inspector-hypo-badge">
        [HYPO] · Observation Only
      </p>
      <h2 className="universe-hub-inspector-title">증거 · 관측 패널</h2>
      <p className="universe-hub-inspector-lead">
        읽기 전용. 실매매·Track A SLA·허브 LLM과 합선되지 않습니다.
      </p>

      {onLogos ? (
        <section className="universe-hub-inspector-block" aria-labelledby="inspector-logos-heading">
          <h3 id="inspector-logos-heading" className="universe-hub-inspector-subtitle">
            Logos 4D topology
          </h3>
          {topology ? (
            <>
              <p className="universe-hub-inspector-meta">
                코퍼스 {topology.n_verses?.toLocaleString() ?? "—"}절 · 정적 스냅샷
              </p>
              {hubs.length > 0 ? (
                <ol className="universe-hub-inspector-list">
                  {hubs.map((hub, idx) => (
                    <li key={`${hub.verse_id}-${idx}`}>
                      {hub.verse_id}
                      {typeof hub.hub_score_inverse_l2 === "number" ? (
                        <span className="universe-hub-inspector-muted">
                          {" "}
                          · hub {hub.hub_score_inverse_l2.toFixed(3)}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="universe-hub-inspector-muted">hub 후보 로딩 중…</p>
              )}
            </>
          ) : (
            <p className="universe-hub-inspector-muted">
              <code>logos_corpus_4d_topology_hub_v1.json</code> 미배포 시 본문 관측소만 참고하세요.
            </p>
          )}
        </section>
      ) : (
        <section className="universe-hub-inspector-block" aria-labelledby="inspector-discover-heading">
          <h3 id="inspector-discover-heading" className="universe-hub-inspector-subtitle">
            원퀘스천 라우터
          </h3>
          <ul className="universe-hub-inspector-list">
            <li>단발 제출 → 플러그인·mkmlife로 분기</li>
            <li>무한 대화 아님 · 허브 LLM 없음</li>
            <li>SEND_GATE: HOLD</li>
          </ul>
        </section>
      )}

      <section className="universe-hub-inspector-block" aria-labelledby="inspector-cta-heading">
        <h3 id="inspector-cta-heading" className="universe-hub-inspector-subtitle">
          B2B 스포크
        </h3>
        <nav className="universe-hub-inspector-links">
          <Link href="/hub/compression">압축 데모 [DRAFT]</Link>
          <Link href="/hub/logos">Logos 관측소</Link>
          <Link href="/hub/customize">패키지 라더 · 상담</Link>
        </nav>
      </section>
    </div>
  );
}
