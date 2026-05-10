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
import {
  KM_CDS_UI_ANALYTICS_EVENTS_V1,
  trackKmCdsUiEvent,
} from "@/lib/km-cds-ui-analytics-events-v1";

const NAV = [
  { id: "chat", label: "대화" },
  { id: "survey", label: "상세 문진" },
  { id: "safety", label: "안전·고지" },
] as const;

function stageLabel(stage: string): string {
  if (stage === "pro") return "Pro";
  if (stage === "standard") return "Standard";
  return "Lite";
}

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
  const [publicDisclaimerAccepted, setPublicDisclaimerAccepted] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem("mkm_public_mode_disclaimer_ack_v1") === "1";
    } catch {
      return false;
    }
  });

  const smartfarmSource = searchParams.get("source") ?? "";
  const showSmartfarmSummary = smartfarmSource === "mkmlab_blueprint";
  const smartfarmStage = stageLabel((searchParams.get("stage") ?? "lite").toLowerCase());
  const smartfarmScore = Number(searchParams.get("score") ?? "0");
  const smartfarmIrrigation = searchParams.get("irrigation") ?? "0";
  const smartfarmLogging = searchParams.get("logging") ?? "0";
  const smartfarmRisk = searchParams.get("risk") ?? "0";
  const smartfarmBudget = searchParams.get("budget") ?? "0";

  useEffect(() => {
    const p = searchParams.get("panel");
    const next = p === "survey" || p === "safety" ? p : "chat";
    setActiveId((cur) => (cur === next ? cur : next));
  }, [searchParams]);

  useEffect(() => {
    if (!ready || !activeThread) return;
    try {
      const k = "mkm_km_cds_public_workspace_mount_v1";
      if (typeof sessionStorage !== "undefined" && sessionStorage.getItem(k)) return;
      if (typeof sessionStorage !== "undefined") sessionStorage.setItem(k, "1");
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.PUBLIC_WORKSPACE_MOUNT_V1, {
        surface: "workspace",
        locale: "ko-KR",
        copy_bundle_id: "km_consumer_workspace_v1",
      });
    } catch {
      // ignore
    }
  }, [ready, activeThread]);

  useEffect(() => {
    return () => {
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.PUBLIC_MODE_EXIT, {
        surface: "workspace",
        locale: "ko-KR",
        copy_bundle_id: "km_consumer_workspace_v1",
      });
    };
  }, []);

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

  const acceptPublicDisclaimer = useCallback(() => {
    try {
      window.localStorage.setItem("mkm_public_mode_disclaimer_ack_v1", "1");
    } catch {
      // ignore storage errors
    }
    setPublicDisclaimerAccepted(true);
    trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.PUBLIC_MODE_ENTER_ACK, {
      surface: "modal",
      locale: "ko-KR",
      copy_bundle_id: "km_public_disclaimer_v1",
    });
  }, []);

  const declinePublicDisclaimer = useCallback(() => {
    trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.PUBLIC_MODE_ENTER_DECLINED, {
      surface: "modal",
      locale: "ko-KR",
      copy_bundle_id: "km_public_disclaimer_v1",
    });
    router.replace("/", { scroll: false });
  }, [router]);

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
      {!publicDisclaimerAccepted ? (
        <div className="workspace-consent-overlay" role="dialog" aria-modal="true" aria-labelledby="public-consent-title">
          <div className="workspace-consent-card">
            <h2 id="public-consent-title">일반 안내 화면으로 전환합니다</h2>
            <p>
              이 화면의 내용은 참고·교육 용도이며 진단이나 치료를 대신하지 않습니다.
              계속하려면 아래 안내에 동의해 주세요.
            </p>
            <p className="workspace-consent-check">
              위 안내를 확인했으며, 표시 정보를 진료 결정에 단독으로 사용하지 않겠습니다.
            </p>
            <div className="workspace-consent-actions">
              <button type="button" className="btn btn-primary" onClick={acceptPublicDisclaimer}>
                동의하고 계속
              </button>
              <button type="button" className="btn btn-ghost" onClick={declinePublicDisclaimer}>
                돌아가기
              </button>
            </div>
          </div>
        </div>
      ) : null}
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
            {showSmartfarmSummary ? (
              <div className="workspace-panel workspace-panel--prose" aria-label="스마트팜 진단 요약">
                <h2 className="workspace-panel-title">스마트팜 진단 결과 연동 완료</h2>
                <p className="workspace-muted">
                  추천 단계: {smartfarmStage} (점수: {smartfarmScore} / 8)
                </p>
                <p className="workspace-muted">
                  세부 값: 관수 {smartfarmIrrigation} · 기록 {smartfarmLogging} · 리스크 {smartfarmRisk} · 예산/인력 {smartfarmBudget}
                </p>
                <p className="workspace-muted">
                  상담 접수 시 이 진단값을 함께 전달해 맞춤형 도입안으로 이어집니다.
                </p>
              </div>
            ) : null}
            <JemaDifferentiationStrip />
            <ConsumerPersistedChat thread={activeThread} onCommit={commitThread} />
          </div>
        ) : null}
        {activeId === "survey" ? (
          <div className="workspace-scroll-panel">
            <PatientPreSurveyForm intakeMode="clinic_v1" />
          </div>
        ) : null}
        {activeId === "safety" ? <ConsumerSafetyPanel /> : null}
      </AppWorkspaceShell>
    </>
  );
}
