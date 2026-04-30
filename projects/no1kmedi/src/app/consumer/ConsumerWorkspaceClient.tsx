"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppWorkspaceShell } from "@/components/AppWorkspaceShell";
import { ConsumerPersistedChat } from "@/components/ConsumerPersistedChat";
import { ConsumerThreadRail } from "@/components/ConsumerThreadRail";
import { JemaDifferentiationStrip } from "@/components/JemaDifferentiationStrip";
import { JemaWorkspaceCommandPalette, type PaletteAction } from "@/components/JemaWorkspaceCommandPalette";
import { PatientPreSurveyForm } from "@/components/PatientPreSurveyForm";
import { useConsumerThreads } from "@/hooks/useConsumerThreads";
import { siteCopy } from "@/content/siteCopy";

const NAV = [
  { id: "chat", label: "대화" },
  { id: "survey", label: "상세 문진" },
  { id: "safety", label: "안전·고지" },
] as const;

function ConsumerSafetyPanel() {
  return (
    <div className="workspace-panel workspace-panel--prose">
      <h2 className="workspace-panel-title">{siteCopy.safety.title}</h2>
      <div className="notice-box">
        <ul>
          {siteCopy.safety.items.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </div>
      <p className="workspace-muted">
        응급 증상이 의심되면 즉시 119 또는 응급실을 이용해 주세요. 본 화면은 의료행위를 대체하지 않습니다.
      </p>
      <p className="workspace-muted">
        대화 기록은 <strong>이 기기 브라우저 localStorage</strong>에만 저장됩니다. 다른 기기·브라우저와 동기화되지
        않으며, 운영 정책에 따라 서버 영속 저장으로 전환할 수 있습니다.
      </p>
    </div>
  );
}

export function ConsumerWorkspaceClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { ready, threads, activeThreadId, setActiveThreadId, activeThread, createThread, deleteThread, commitThread } =
    useConsumerThreads();

  const [activeId, setActiveId] = useState<string>(() => {
    const p = searchParams.get("panel");
    return p === "survey" || p === "safety" ? p : "chat";
  });

  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const p = searchParams.get("panel");
    const next = p === "survey" || p === "safety" ? p : "chat";
    setActiveId((cur) => (cur === next ? cur : next));
  }, [searchParams]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toLowerCase().includes("mac");
      if ((isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onSelect = useCallback(
    (id: string) => {
      setActiveId(id);
      const path = id === "chat" ? "/consumer" : `/consumer?panel=${encodeURIComponent(id)}`;
      router.replace(path, { scroll: false });
    },
    [router],
  );

  const startNewChat = useCallback(() => {
    createThread();
    setActiveId("chat");
    router.replace("/consumer", { scroll: false });
  }, [createThread, router]);

  const paletteActions: PaletteAction[] = useMemo(
    () => [
      { id: "chat", label: "대화 화면", hint: "panel", run: () => onSelect("chat") },
      { id: "survey", label: "상세 문진", hint: "panel", run: () => onSelect("survey") },
      { id: "safety", label: "안전·고지", hint: "panel", run: () => onSelect("safety") },
      { id: "new", label: "새 대화", hint: "스레드", run: () => startNewChat() },
      { id: "home", label: "랜딩으로", hint: "/", run: () => router.push("/") },
    ],
    [onSelect, router, startNewChat],
  );

  const sidebarBody =
    ready && threads.length ? (
      <ConsumerThreadRail
        threads={threads}
        activeId={activeThreadId}
        onSelect={(id) => {
          setActiveThreadId(id);
          setActiveId("chat");
          router.replace("/consumer", { scroll: false });
        }}
        onDelete={deleteThread}
      />
    ) : null;

  if (!ready || !activeThread) {
    return (
      <div className="workspace-fallback" role="status" aria-live="polite">
        대화 저장소를 불러오는 중…
      </div>
    );
  }

  return (
    <>
      <JemaWorkspaceCommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} actions={paletteActions} />
      <AppWorkspaceShell
        homeHref="/"
        roleLabel="일반인"
        nav={[...NAV]}
        activeId={activeId}
        onSelect={onSelect}
        sidebarBody={sidebarBody}
        sidebarFooter={
          <button type="button" className="workspace-secondary-btn" onClick={startNewChat}>
            새 대화
          </button>
        }
      >
        {activeId === "chat" ? (
          <div className="workspace-chat-column">
            <JemaDifferentiationStrip />
            <ConsumerPersistedChat thread={activeThread} onCommit={commitThread} />
          </div>
        ) : null}
        {activeId === "survey" ? (
          <div className="workspace-scroll-panel">
            <PatientPreSurveyForm />
          </div>
        ) : null}
        {activeId === "safety" ? <ConsumerSafetyPanel /> : null}
      </AppWorkspaceShell>
    </>
  );
}
