"use client";

import {
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

const STORAGE_KEY = "mkm_hub_inspector_width_v1";
export const HUB_INSPECTOR_WIDTH_MIN = 200;
export const HUB_INSPECTOR_WIDTH_MAX = 420;
export const HUB_INSPECTOR_WIDTH_DEFAULT = 280;

export function useHubInspectorWidthV3() {
  const [width, setWidth] = useState(HUB_INSPECTOR_WIDTH_DEFAULT);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = Number(raw);
      if (parsed >= HUB_INSPECTOR_WIDTH_MIN && parsed <= HUB_INSPECTOR_WIDTH_MAX) {
        setWidth(parsed);
      }
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  const persistWidth = useCallback((next: number) => {
    const clamped = Math.min(
      HUB_INSPECTOR_WIDTH_MAX,
      Math.max(HUB_INSPECTOR_WIDTH_MIN, next),
    );
    setWidth(clamped);
    try {
      localStorage.setItem(STORAGE_KEY, String(clamped));
    } catch {
      /* ignore */
    }
  }, []);

  return { width, persistWidth };
}

type HubInspectorResizeHandleV3Props = {
  onResize: (width: number) => void;
  currentWidth: number;
};

export function HubInspectorResizeHandleV3({
  onResize,
  currentWidth,
}: HubInspectorResizeHandleV3Props) {
  const dragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(currentWidth);

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      dragging.current = true;
      startX.current = event.clientX;
      startWidth.current = currentWidth;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [currentWidth],
  );

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      if (!dragging.current) return;
      const delta = startX.current - event.clientX;
      onResize(startWidth.current + delta);
    },
    [onResize],
  );

  const onPointerUp = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    dragging.current = false;
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      /* already released */
    }
  }, []);

  return (
    <button
      type="button"
      className="universe-hub-inspector-resize-handle"
      aria-label="Resize observation panel"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    />
  );
}
