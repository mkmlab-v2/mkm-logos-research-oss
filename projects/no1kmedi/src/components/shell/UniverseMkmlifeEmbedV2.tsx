"use client";

import { useState } from "react";
import {
  buildMkmlifeEmbedSrc,
  isMkmlifeEmbedEnabled,
  type MkmlifeEmbedView,
} from "@/lib/universeHubMkmlifeEmbedV2";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

type Props = {
  prefill?: string;
  view?: MkmlifeEmbedView;
};

export function UniverseMkmlifeEmbedV2({ prefill, view = "ask-one" }: Props) {
  const [loadFailed, setLoadFailed] = useState(false);

  if (!isMkmlifeEmbedEnabled()) {
    return null;
  }

  const src = buildMkmlifeEmbedSrc({ prefill, view });
  const externalHref = prefill?.trim()
    ? `${UNIVERSE_HUB_DEEP_LINKS.mkmlifeAskOne}?prefill=${encodeURIComponent(prefill.trim())}&source=jema_hub_v2`
    : `${UNIVERSE_HUB_DEEP_LINKS.mkmlifeAskOne}?source=jema_hub_v2`;

  return (
    <section className="universe-hub-mkmlife-embed" aria-labelledby="mkmlife-embed-title">
      <h2 id="mkmlife-embed-title" className="universe-hub-section-title">
        MKM LIFE · consumer_portal_v1
      </h2>
      <p className="universe-hub-embed-note">
        Air-gap iframe — mkmlife.com 백엔드·운영자 패널·허브 LLM과 미합선. [NON-MEDICAL] · [RESEARCH_ONLY]
      </p>
      {loadFailed ? (
        <p className="universe-hub-plugin-body">
          iframe을 불러오지 못했습니다.{" "}
          <a href={externalHref} target="_blank" rel="noopener noreferrer">
            MKM LIFE에서 새 탭으로 열기
          </a>
        </p>
      ) : (
        <div className="universe-hub-mkmlife-embed-frame">
          <iframe
            title="MKM LIFE consumer portal"
            src={src}
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            onError={() => setLoadFailed(true)}
          />
        </div>
      )}
      <p className="universe-hub-disclaimer">SEND_GATE HOLD · 실고객 코퍼스 업로드 UI 없음</p>
    </section>
  );
}
