import { PersonadiaryChrome } from "@/components/PersonadiaryChrome";
import { PersonadiaryPremiumHome } from "@/components/personadiary/PersonadiaryPremiumHome";
import { PersonadiaryWaitlist } from "@/components/PersonadiaryWaitlist";
import {
  personadiaryCopy,
  personadiaryWaitlistEmbedUrl,
} from "@/content/personadiaryCopy";

export const dynamic = "force-dynamic";

export default function PersonaDiaryPreviewPage() {
  return (
    <PersonadiaryChrome premium>
      <main id="main" className="pd-main-premium pd-main-premium--ios-bridge">
        <PersonadiaryPremiumHome />

        <PersonadiaryWaitlist embedUrl={personadiaryWaitlistEmbedUrl()} />

        <section
          id="safety"
          className="pd-premium-safety"
          aria-labelledby="pd-safety-title"
        >
          <div className="pd-premium-section-inner">
            <h2 id="pd-safety-title">안전·면책 고지</h2>
            <div className="notice-box pd-glass">
              <ul>
                <li>
                  본 페이지는 콘셉트 프리뷰이며, 의료·투자·법률 의사결정을
                  대체하지 않습니다.
                </li>
                <li>
                  비예측형 성찰 · 명리=오늘의 흐름·질문거리 · 예언·적중·%·운세 단정 없음.
                </li>
                <li>
                  성과 보장, 무손실 완성, Track A/실매매 자동 합선 주장을 하지
                  않습니다.
                </li>
                <li>
                  심화 분석·관측은{" "}
                  <a
                    href={personadiaryCopy.links.observatory}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    jemaai.cloud v6
                  </a>
                  등 별도 도메인에서 제공됩니다.
                </li>
              </ul>
            </div>
          </div>
        </section>
      </main>
    </PersonadiaryChrome>
  );
}
