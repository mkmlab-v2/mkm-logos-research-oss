import { Suspense } from "react";
import { MkmCallbackClient } from "./MkmCallbackClient";

export default function MkmFamilyAuthCallbackPage() {
  return (
    <main className="universe-hub-page" style={{ padding: "2rem", maxWidth: "28rem", margin: "0 auto" }}>
      <Suspense fallback={<p>MKM Family 계정 연결 중…</p>}>
        <MkmCallbackClient />
      </Suspense>
    </main>
  );
}
