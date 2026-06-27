import { Suspense } from "react";

import { LogosAgentClaimClient } from "./LogosAgentClaimClient";

export default function LogosAgentClaimPage() {
  return (
    <Suspense fallback={<main style={{ padding: "2rem 1rem" }}>로딩 중…</main>}>
      <LogosAgentClaimClient />
    </Suspense>
  );
}
