import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

export function UniverseReportsEmptyV2() {
  return (
    <div className="universe-hub-empty-state" role="status">
      <p className="universe-hub-empty-title">허브에는 저장된 리포트가 없습니다</p>
      <p className="universe-hub-empty-body">
        원퀘스천·발행 리포트는 mkmlife.com 계정 면에서 확인합니다. 허브는 라우터만 담당합니다.
      </p>
      <div className="universe-hub-plugin-actions">
        <a className="universe-hub-cta universe-hub-cta--primary" href={UNIVERSE_HUB_DEEP_LINKS.mkmlifeReports}>
          MKM LIFE 내 리포트 열기 ↗
        </a>
        <a className="universe-hub-cta universe-hub-cta--ghost" href={UNIVERSE_HUB_DEEP_LINKS.mkmlifeAskOne}>
          새 원퀘스천 작성 ↗
        </a>
      </div>
    </div>
  );
}
