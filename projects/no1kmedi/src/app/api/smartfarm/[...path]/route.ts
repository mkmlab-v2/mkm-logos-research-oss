import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function upstreamBase(): string {
  const raw =
    process.env.SMARTFARM_API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_SMARTFARM_API_BASE_URL?.trim() ||
    "http://127.0.0.1:8020";
  return raw.replace(/\/$/, "");
}

type RouteCtx = { params: { path?: string[] } };

async function proxy(req: NextRequest, ctx: RouteCtx): Promise<NextResponse> {
  const segments = ctx.params.path ?? [];
  const path = segments.map((s) => encodeURIComponent(s)).join("/");
  const incoming = new URL(req.url);
  const target = `${upstreamBase()}/${path}${incoming.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  let body: string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.text();
  }

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "upstream_unreachable";
    return NextResponse.json(
      {
        ok: false,
        error: message,
        upstream: upstreamBase(),
        hint: "Start: py -m uvicorn scripts.ai_smartfarm_api_stub:app --host 127.0.0.1 --port 8020",
      },
      { status: 502 },
    );
  }
}

export async function GET(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx);
}

export async function PUT(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx);
}
