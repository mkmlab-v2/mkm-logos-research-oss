/** 클라이언트 측 타이핑 효과(서버는 여전히 JSON 한 번). 토큰 스트리밍은 추후 SSE로 교체 가능. */
export function streamTextClient(full: string, onPartial: (s: string) => void): Promise<void> {
  const chars = Array.from(full);
  if (chars.length === 0) {
    onPartial("");
    return Promise.resolve();
  }

  const reducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reducedMotion) {
    onPartial(full);
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let i = 0;
    const step = Math.max(2, Math.min(6, Math.ceil(chars.length / 120)));
    const frame = () => {
      i += step;
      if (i >= chars.length) {
        onPartial(full);
        resolve();
        return;
      }
      onPartial(chars.slice(0, i).join(""));
      window.requestAnimationFrame(() => window.setTimeout(frame, 10));
    };
    frame();
  });
}
