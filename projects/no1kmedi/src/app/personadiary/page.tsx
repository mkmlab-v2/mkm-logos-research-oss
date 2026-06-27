import { PersonadiaryChrome } from "@/components/PersonadiaryChrome";
import { PersonadiaryPremiumHome } from "@/components/personadiary/PersonadiaryPremiumHome";
import { PersonadiaryWaitlist } from "@/components/PersonadiaryWaitlist";
import {
  personadiaryCopy,
  personadiaryWaitlistEmbedUrl,
} from "@/content/personadiaryCopy";
import { loadDailyGuidePackage } from "@/lib/personadiaryDailyGuide";

export const dynamic = "force-dynamic";

export default async function PersonaDiaryPreviewPage() {
  const initialPackage = await loadDailyGuidePackage(null);

  return (
    <PersonadiaryChrome premium>
      <main id="main" className="pd-main-premium pd-main-premium--ios-bridge">
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var k='pd_commercial_dom_guard_v1';var m='pd-commercial-home-ssot';function gone(){return!document.querySelector('.'+m);}function reload(key){if(sessionStorage.getItem(key))return;sessionStorage.setItem(key,'1');var u=new URL(location.href);u.searchParams.set('v',String(Date.now()));location.replace(u.toString());}if(typeof location!=='undefined'&&(location.hostname==='localhost'||location.hostname==='127.0.0.1')){if(gone())reload(k);else{try{new MutationObserver(function(){if(gone())reload(k);}).observe(document.documentElement,{childList:true,subtree:true});}catch(e){}}}function apexHost(h){return h==='personadiary.com'||h==='www.personadiary.com'||h==='preview.personadiary.com';}function ritualStale(){var draw=document.querySelector('.pd-ritual-draw');if(!draw)return false;if(document.querySelector('[data-testid="pd-ritual-status-slot"]'))return false;return Boolean(draw.querySelector('.pd-orb-status')||draw.querySelector('.pd-orb-legend'));}function runRitualGuard(){if(typeof location==='undefined'||!apexHost(location.hostname))return;if(!ritualStale())return;reload('pd_ritual_layout_guard_v1');}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(runRitualGuard,900);});else setTimeout(runRitualGuard,900);})();`,
          }}
        />
        <PersonadiaryPremiumHome initialPackage={initialPackage} />

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
                  비예측형 성찰 · A-Code=오늘의 흐름·질문거리 · 예언·적중·%·운세 단정 없음.
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
