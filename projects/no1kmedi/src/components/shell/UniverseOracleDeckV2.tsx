import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

const EVENTS = [
  {
    id: "deck",
    date: "관측 덱",
    title: "공개 관측 보드",
    body: "jemaai.cloud 정적 전광판 — Track A 헤드라인·실매매 트리거 없음.",
    href: UNIVERSE_HUB_DEEP_LINKS.jemaaiShowroom,
    external: true,
  },
  {
    id: "life-news",
    date: "소비자 레인",
    title: "MKM LIFE 관측 카드",
    body: "뉴스·관측 덱은 mkmlife consumer_portal_v1 — 허브와 백엔드 미합선.",
    href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeNewsDeck,
    external: true,
  },
  {
    id: "btrack",
    date: "B-track",
    title: "리서치 전용 라벨",
    body: "예언·매크로 수치는 [HYPO]·research_only. 본선 주문·승격 게이트와 분리.",
    href: "/hub/customize",
    external: false,
  },
] as const;

export function UniverseOracleDeckV2() {
  return (
    <ol className="universe-hub-timeline">
      {EVENTS.map((ev, index) => (
        <li key={ev.id} className="universe-hub-timeline-item">
          <span className="universe-hub-timeline-index">{String(index + 1).padStart(2, "0")}</span>
          <div className="universe-hub-timeline-card">
            <p className="universe-hub-timeline-date">{ev.date}</p>
            <h3 className="universe-hub-timeline-title">{ev.title}</h3>
            <p className="universe-hub-timeline-body">{ev.body}</p>
            {ev.external ? (
              <a
                className="universe-hub-timeline-link"
                href={ev.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                열기 ↗
              </a>
            ) : (
              <a className="universe-hub-timeline-link" href={ev.href}>
                B2B 가드 소개
              </a>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
