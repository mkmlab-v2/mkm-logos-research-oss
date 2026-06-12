import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseCompressionSandboxV2 } from "@/components/shell/UniverseCompressionSandboxV2";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";

export const metadata = {
  title: "압축 데모 샌드박스 — JEMA AI Hub",
};

type Props = {
  searchParams?: { prefill?: string };
};

export default function HubCompressionPage({ searchParams }: Props) {
  const prefill = searchParams?.prefill;
  return (
    <div className="universe-hub-plugin-stack">
      <HubPrefillBannerV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="compression_sandbox"
        title="토큰 압축 데모 샌드박스"
        body="B2B PoC용 오프라인 시뮬레이터. /hub/developer의 API·오픈벤치와 분리된 체험 면입니다."
        primaryCta={{ href: "/enterprise/apply", label: "B2B 상담·사전 감사 신청" }}
        secondaryCta={{ href: "/hub/developer", label: "개발자 샌드박스" }}
        phaseNote="Hub UI Chassis v3 · compression spoke"
      />
      <UniverseCompressionSandboxV2 />
    </div>
  );
}
