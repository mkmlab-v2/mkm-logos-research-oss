"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { HUB_INSPECTOR_ARTIFACTS_V1 } from "@/lib/universeHubInspectorArtifactsV1";
import {
  LOGOS_RESEARCH_STUDIO,
} from "@/lib/universeHubLogosCommercialV1";
import {
  UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH,
  type LogosTopologyHubV1,
  isLogosTopologyHubV1,
} from "@/lib/universeHubLogosTopologyV1";

export function HubEvidenceInspectorV3() {
  const pathname = usePathname() ?? "";
  const onLogos = pathname.startsWith("/hub/logos");
  const onDiscover = pathname.replace(/\/$/, "") === "/hub";
  const [topology, setTopology] = useState<LogosTopologyHubV1 | null>(null);

  useEffect(() => {
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
  }, [pathname]);

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

      <section className="universe-hub-inspector-block" aria-labelledby="inspector-artifacts-heading">
        <h3 id="inspector-artifacts-heading" className="universe-hub-inspector-subtitle">
          Logos Observatory · 아티팩트
        </h3>
        <p className="universe-hub-inspector-meta">
          [HYPO] · research_only · 성경 렌즈 [NON_GATING]
        </p>
        {!onDiscover ? (
          <>
            <p className="universe-hub-inspector-cta-row">
              <Link href={LOGOS_RESEARCH_STUDIO} className="universe-hub-inspector-cta-primary">
                Graph Studio 열기 (상용 · on-domain)
              </Link>
            </p>
            <ul className="universe-hub-inspector-list">
              {HUB_INSPECTOR_ARTIFACTS_V1.map((artifact) => (
                <li key={artifact.id}>
                  {artifact.external ? (
                    <a href={artifact.href} target="_blank" rel="noopener noreferrer">
                      {artifact.labelKo}
                    </a>
                  ) : (
                    <Link href={artifact.href}>{artifact.labelKo}</Link>
                  )}
                  {artifact.repoPath ? (
                    <div className="universe-hub-artifact-path">{artifact.repoPath}</div>
                  ) : null}
                </li>
              ))}
            </ul>
            {topology ? (
              <p className="universe-hub-inspector-meta">
                topology loaded · {topology.n_verses?.toLocaleString() ?? "—"} verses
                {topology.generated_at_utc ? ` · ${topology.generated_at_utc}` : ""}
              </p>
            ) : (
              <p className="universe-hub-inspector-muted">
                JSON 미배포 — <code>logos_corpus_4d_topology_hub_v1.json</code> 또는{" "}
                <Link href="/hub/logos">/hub/logos</Link> spoke 참고.
              </p>
            )}
          </>
        ) : (
          <div className="universe-hub-inspector-discover-summary" data-hub-inspector-discover-summary="1">
            <p className="universe-hub-inspector-cta-row">
              <Link href={LOGOS_RESEARCH_STUDIO} className="universe-hub-inspector-cta-primary">
                Graph Studio 열기
              </Link>
            </p>
            <ul className="universe-hub-inspector-list">
              {HUB_INSPECTOR_ARTIFACTS_V1.slice(0, 3).map((artifact) => (
                <li key={artifact.id}>
                  {artifact.external ? (
                    <a href={artifact.href} target="_blank" rel="noopener noreferrer">
                      {artifact.labelKo}
                    </a>
                  ) : (
                    <Link href={artifact.href}>{artifact.labelKo}</Link>
                  )}
                </li>
              ))}
            </ul>
            <p className="universe-hub-inspector-more-link">
              <Link href="/hub/logos">Logos Observatory 더 보기 →</Link>
            </p>
          </div>
        )}
      </section>

      {onLogos ? (
        <section className="universe-hub-inspector-block" aria-labelledby="inspector-logos-heading">
          <h3 id="inspector-logos-heading" className="universe-hub-inspector-subtitle">
            Logos 4D topology (live)
          </h3>
          {topology ? (
            <>
              <p className="universe-hub-inspector-meta">
                코퍼스 {topology.n_verses?.toLocaleString() ?? "—"}절 · 정적 스냅샷
              </p>
              {topology.reproduce_command ? (
                <p className="universe-hub-artifact-path">{topology.reproduce_command}</p>
              ) : null}
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
                <p className="universe-hub-inspector-muted">hub 후보 없음</p>
              )}
            </>
          ) : (
            <p className="universe-hub-inspector-muted">
              <code>logos_corpus_4d_topology_hub_v1.json</code> 미배포 — 본문 관측소만 참고.
            </p>
          )}
        </section>
      ) : null}

      {!onDiscover ? (
      <section className="universe-hub-inspector-block" aria-labelledby="inspector-cta-heading">
        <h3 id="inspector-cta-heading" className="universe-hub-inspector-subtitle">
          B2B 스포크
        </h3>
        <nav className="universe-hub-inspector-links">
          <Link href={LOGOS_RESEARCH_STUDIO}>Graph Studio (상용)</Link>
          <Link href="/hub/compression">압축 데모 [DRAFT]</Link>
          <Link href="/hub/logos">Logos 관측소</Link>
          <Link href="/hub/life">라이프 케어</Link>
          <Link href="/hub/customize">패키지 라더 · 상담</Link>
        </nav>
      </section>
      ) : null}
    </div>
  );
}
