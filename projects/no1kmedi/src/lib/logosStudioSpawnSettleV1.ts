import type { ChildProcess } from "node:child_process";

/** Kill a hung child and resolve even if `close` never fires (Windows SIGTERM). */
export function settleChildOrTimeout<T>(
  child: ChildProcess,
  timeoutMs: number,
  resolve: (value: T) => void,
  timeoutValue: T,
): { settle: (value: T) => void } {
  let settled = false;
  const settle = (value: T) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    resolve(value);
  };
  const timer = setTimeout(() => {
    try {
      child.kill("SIGTERM");
    } catch {
      /* ignore */
    }
    settle(timeoutValue);
  }, Math.max(1, timeoutMs));
  return { settle };
}
