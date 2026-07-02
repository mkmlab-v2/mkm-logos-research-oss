import { NextRequest } from "next/server";

import { POST as queryPost } from "../query/route";

/** @deprecated Use POST /api/logos-research/query with output_format=inquiry_report_v1 */
export async function POST(request: NextRequest) {
  const body = (await request.json()) as Record<string, unknown>;
  const merged = {
    ...body,
    output_format: "inquiry_report_v1",
    query: body.query ?? body.question,
  };
  const proxy = new NextRequest(request.url, {
    method: "POST",
    headers: request.headers,
    body: JSON.stringify(merged),
  });
  return queryPost(proxy);
}
