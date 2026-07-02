"use client";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Minimal SSE parser for logos inquiry stream (browser). */
export async function consumeLogosInquirySse(
  response: Response,
  handlers: {
    onSnapshot?: (data: unknown) => void;
    onS4Delta?: (text: string, index: number) => void;
    onS4Done?: (body: string) => void;
    onDone?: (report: unknown) => void;
    onError?: (message: string) => void;
    /** Optional visual pacing between S4 chunks (ms). Server may also pace via LOGOS_INQUIRY_STREAM_CHUNK_MS. */
    paceMs?: number;
  },
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("no_response_body");
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatchBlock = async (block: string) => {
    const lines = block.split("\n");
    let eventName = "message";
    let dataLine = "";
    for (const line of lines) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) dataLine = line.slice(5).trim();
    }
    if (!dataLine) return;
    const parsed = JSON.parse(dataLine) as {
      event?: string;
      snapshot?: unknown;
      delta?: { text: string; index: number };
      s4?: { body_ko: string };
      report?: unknown;
    };
    const ev = parsed.event || eventName;
    if (ev === "snapshot") {
      handlers.onSnapshot?.(parsed.snapshot);
      return;
    }
    if (ev === "s4_delta" && parsed.delta) {
      if (handlers.paceMs && handlers.paceMs > 0) await sleep(handlers.paceMs);
      handlers.onS4Delta?.(parsed.delta.text, parsed.delta.index);
      return;
    }
    if (ev === "s4_done" && parsed.s4) handlers.onS4Done?.(parsed.s4.body_ko);
    if (ev === "done" && parsed.report) handlers.onDone?.(parsed.report);
    if (ev === "error") {
      const msg =
        typeof (parsed as { message?: string }).message === "string"
          ? (parsed as { message: string }).message
          : "stream_error";
      handlers.onError?.(msg);
      throw new Error(msg);
    }
  };

  const flushBuffer = async () => {
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      if (block.trim()) await dispatchBlock(block);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: !done });
    await flushBuffer();
    if (done) {
      buffer += decoder.decode();
      await flushBuffer();
      if (buffer.trim()) await dispatchBlock(buffer);
      break;
    }
  }
}
