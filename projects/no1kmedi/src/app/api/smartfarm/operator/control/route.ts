import { NextRequest, NextResponse } from "next/server";

import {
  SMARTFARM_CONTROL_ZONE_ID,
  SMARTFARM_INTERLOCK_PAIRS,
  SMARTFARM_PILOT_FARM_ID,
  SMARTFARM_VALVE_CHANNELS,
} from "@/lib/smartfarmOperatorConfig";

export const runtime = "nodejs";

type ControlBody = {
  channel_id?: string;
  action?: "open" | "close";
  mode?: "remote_manual" | "onsite_manual";
  reason_code?: "manual_override" | "emergency_stop";
  requested_by?: string;
};

function upstreamBase(): string {
  const raw =
    process.env.SMARTFARM_API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_SMARTFARM_API_BASE_URL?.trim() ||
    "http://127.0.0.1:8020";
  return raw.replace(/\/$/, "");
}

function isKnownChannel(channelId: string): boolean {
  return SMARTFARM_VALVE_CHANNELS.some((c) => c.channel_id === channelId);
}

function interlockBlocked(
  channelId: string,
  action: string,
  openChannels: Set<string>,
): string | null {
  if (action !== "open") return null;
  for (const [a, b] of SMARTFARM_INTERLOCK_PAIRS) {
    if (channelId === a && openChannels.has(b)) {
      return `interlock:${a}+${b}`;
    }
    if (channelId === b && openChannels.has(a)) {
      return `interlock:${a}+${b}`;
    }
  }
  return null;
}

export async function POST(request: NextRequest) {
  let body: ControlBody;
  try {
    body = (await request.json()) as ControlBody;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const channelId = String(body.channel_id || "").trim();
  const action = body.action === "close" ? "close" : body.action === "open" ? "open" : null;
  if (!channelId || !action || !isKnownChannel(channelId)) {
    return NextResponse.json({ ok: false, error: "invalid_channel_or_action" }, { status: 400 });
  }

  const openHeader = request.headers.get("x-sf-open-channels");
  const openChannels = new Set(
    (openHeader || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  const blocked = interlockBlocked(channelId, action, openChannels);
  if (blocked) {
    return NextResponse.json({ ok: false, error: blocked }, { status: 409 });
  }

  const now = new Date().toISOString();
  const commandId = `cmd_${SMARTFARM_PILOT_FARM_ID}_${channelId}_${action}_${Date.now()}`;
  const reason =
    body.reason_code === "emergency_stop" ? "emergency_stop" : "manual_override";
  const mode = body.mode === "onsite_manual" ? "onsite_manual" : "remote_manual";

  const payload = {
    farm_id: SMARTFARM_PILOT_FARM_ID,
    zone_id: SMARTFARM_CONTROL_ZONE_ID,
    ts_utc: now,
    timezone: "Asia/Seoul",
    command_id: commandId,
    mode,
    target: "valve",
    action,
    reason_code: reason,
    max_runtime_sec: action === "open" ? 300 : 30,
    estimated_volume_liter: 0,
    requested_by: body.requested_by || "smartfarm_operator_ui",
  };

  try {
    const upstream = await fetch(`${upstreamBase()}/v1/control`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const text = await upstream.text();
    let parsed: unknown = null;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = { raw: text };
    }
    if (!upstream.ok) {
      return NextResponse.json(
        { ok: false, error: "upstream_control_failed", upstream: parsed },
        { status: upstream.status },
      );
    }
    return NextResponse.json({
      ok: true,
      command_id: commandId,
      channel_id: channelId,
      action,
      upstream: parsed,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "upstream_unreachable";
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}
