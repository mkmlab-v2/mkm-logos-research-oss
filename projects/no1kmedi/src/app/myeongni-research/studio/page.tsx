import { Suspense } from "react";

import { MyeongniResearchStudioPageBody } from "@/components/myeongni-research/MyeongniResearchStudioPageBody";

export default function MyeongniResearchStudioPage() {
  return (
    <Suspense fallback={<p className="mn-studio-loading">스튜디오 로딩 중…</p>}>
      <MyeongniResearchStudioPageBody />
    </Suspense>
  );
}
