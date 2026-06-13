import Link from "next/link";
import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

export const metadata = {
  title: "개발자 샌드박스 — JEMA AI Hub",
};

const SNIPPET = `curl -sS https://a-codeai.com/api/v1/health \\
  -H "Authorization: Bearer $ACODE_API_KEY"`;

type Props = {
  searchParams?: { prefill?: string };
};

export default function HubDeveloperPage({ searchParams }: Props) {
  const prefill = searchParams?.prefill;
  return (
    <div className="universe-hub-plugin-stack">
      <HubPrefillBannerV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="a_code_sandbox"
        title="개발자 샌드박스"
        body="압축 API·오픈 벤치·토큰 미터링은 a-codeai.com B2B 면에서 제공됩니다. Track A 헤드라인 수치는 대외 카피에 사용하지 않습니다."
        primaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.aCodeLanding,
          label: "A-Code AI 랜딩",
          external: true,
        }}
        secondaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.aCodeOpenBenchBenchmark,
          label: "오픈 벤치 랜딩 ↗",
          external: true,
        }}
        phaseNote="P2 · 스니펫 + benchmark + GitHub reproduce"
      />
      <section className="universe-hub-open-bench-note" aria-labelledby="open-bench-heading">
        <h2 id="open-bench-heading" className="universe-hub-section-title">
          Community open-bench (GitHub)
        </h2>
        <p className="universe-hub-section-lead">
          슬림 공개 미러 — 로컬에서 evidence chain·golden40 routed PoC를 재현합니다.{" "}
          <code>contributor_provided</code> JSONL 기여는 CONTRIBUTING 가이드를 따릅니다.
        </p>
        <p className="universe-hub-disclaimer universe-hub-disclaimer--compact">
          SEND_GATE: HOLD · per-SKU metrics only · frozen Track A SLA 헤드라인과 동일시 금지 · B→A 자동 합선 없음
        </p>
        <div className="universe-hub-plugin-actions">
          <a
            className="universe-hub-cta universe-hub-cta--ghost"
            href={UNIVERSE_HUB_DEEP_LINKS.aCodeOpenBenchBenchmark}
            target="_blank"
            rel="noopener noreferrer"
          >
            a-codeai.com/benchmark ↗
          </a>
          <a
            className="universe-hub-cta universe-hub-cta--ghost"
            href={UNIVERSE_HUB_DEEP_LINKS.aCodeOpenBenchReproduce}
            target="_blank"
            rel="noopener noreferrer"
          >
            mkmlab-v2/a-codeai-compression-reproduce ↗
          </a>
        </div>
        <Link className="universe-hub-inline-link" href="/enterprise">
          엔터프라이즈 · positioning deck (internal)
        </Link>
        <Link className="universe-hub-inline-link" href={UNIVERSE_HUB_DEEP_LINKS.compressionPilotApply}>
          Tier-0 pre-audit apply
        </Link>
      </section>
      <section aria-labelledby="dev-snippet-heading">
        <h2 id="dev-snippet-heading" className="universe-hub-section-title">
          연결 예시 (PoC)
        </h2>
        <pre className="universe-hub-code-snippet">
          <code>{SNIPPET}</code>
        </pre>
      </section>
    </div>
  );
}
