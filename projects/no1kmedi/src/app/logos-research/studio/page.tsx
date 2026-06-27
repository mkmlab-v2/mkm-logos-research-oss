import { Suspense } from "react";

import { LogosResearchStudioPageBody } from "@/components/logos-research/LogosResearchStudioPageBody";

export default function LogosResearchStudioPage() {
  return (
    <div data-logos-studio-route="1" className="logos-research-studio-route">
      <Suspense fallback={<p className="lr-section-lead">스튜디오 로딩 중…</p>}>
        <LogosResearchStudioPageBody />
      </Suspense>
    </div>
  );
}
