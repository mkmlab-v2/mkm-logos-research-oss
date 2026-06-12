import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

const BENEFITS = [
  {
    id: "ask-one",
    title: "원퀘스천 리포트",
    body: "한 문장 질문 → 단발 리포트 완결. 무한 스레드·챗봇이 아닙니다.",
    href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeAskOne,
  },
  {
    id: "deck",
    title: "관측 카드 덱",
    body: "웰니스·관측 카드는 mkmlife에서 소비. 허브는 딥링크만 제공합니다.",
    href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeNewsDeck,
  },
  {
    id: "reports",
    title: "내 리포트 원장",
    body: "발행 리포트·다운로드는 계정 면에서 확인 — 데이터 격벽 유지.",
    href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeReports,
  },
] as const;

export function UniverseLifeBenefitsV2() {
  return (
    <ul className="universe-hub-benefits">
      {BENEFITS.map((b) => (
        <li key={b.id} className="universe-hub-benefit-card">
          <h3 className="universe-hub-benefit-title">{b.title}</h3>
          <p className="universe-hub-benefit-body">{b.body}</p>
          <a className="universe-hub-benefit-link" href={b.href} target="_blank" rel="noopener noreferrer">
            mkmlife에서 열기 ↗
          </a>
        </li>
      ))}
    </ul>
  );
}
