"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { LogosResearchStudioClient } from "@/components/logos-research/LogosResearchStudioClient";
import { LogosResearchSiteChrome } from "@/components/logos-research/LogosResearchSiteChrome";
import { logosResearchCopy } from "@/content/logosResearchCopy";

const studio = "studio" in logosResearchCopy ? logosResearchCopy.studio : null;

export function LogosResearchStudioPageBody() {
  const searchParams = useSearchParams();
  const embedHero = searchParams.get("embed") === "hero";

  return (
    <div
      className={`logos-research-page logos-research-studio-theme logos-research-studio-theme--scriptorium${embedHero ? " lr-studio--embed-hero" : ""}`}
      data-logos-studio-shell="1"
    >
      {!embedHero ? <LogosResearchSiteChrome active="studio" /> : null}
      <main id="main" className="lr-studio-main">
        {!embedHero ? (
          <section className="lr-hero lr-studio-hero lr-studio-hero--compact">
            <h1>{studio?.hero_title ?? "Logos Graph Studio"}</h1>
            <p className="lr-hero-lead lr-studio-hero-lead">
              {studio?.hero_lead ?? "질문 → GraphRAG 경로 → 구절 참조"}
            </p>
          </section>
        ) : null}
        <Suspense fallback={<p className="lr-section-lead">{studio?.loading ?? "스튜디오 로딩 중…"}</p>}>
          <LogosResearchStudioClient embedHero={embedHero} />
        </Suspense>
      </main>
    </div>
  );
}
