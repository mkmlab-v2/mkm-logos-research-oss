import { NextResponse } from "next/server";

import { logosProtectedResourceMetadata } from "@/lib/logosAgentAuthDiscoveryV1";

export const runtime = "edge";

export async function GET() {
  return NextResponse.json(logosProtectedResourceMetadata(), {
    headers: {
      "Cache-Control": "public, max-age=300",
      "Content-Type": "application/json",
    },
  });
}
