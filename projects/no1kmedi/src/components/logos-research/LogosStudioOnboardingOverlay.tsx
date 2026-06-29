"use client";

import { useState } from "react";

import type { LogosStudioAudienceMode } from "@/lib/logosStudioAudienceModeV1";
import {
  LOGOS_STUDIO_ONBOARDING_TOPICS,
  type LogosStudioOnboardingResult,
  type LogosStudioOnboardingTopic,
} from "@/lib/logosStudioOnboardingV1";

type Props = {
  onComplete: (result: LogosStudioOnboardingResult) => void;
  onSkip: () => void;
};

export function LogosStudioOnboardingOverlay({ onComplete, onSkip }: Props) {
  const [step, setStep] = useState<1 | 2>(1);
  const [audienceMode, setAudienceMode] = useState<LogosStudioAudienceMode>("academic");
  const [topicId, setTopicId] = useState(LOGOS_STUDIO_ONBOARDING_TOPICS[0]?.id ?? "job");

  const selectedTopic =
    LOGOS_STUDIO_ONBOARDING_TOPICS.find((t) => t.id === topicId) ??
    LOGOS_STUDIO_ONBOARDING_TOPICS[0];

  const finish = (topic: LogosStudioOnboardingTopic) => {
    onComplete({ audienceMode, topic });
  };

  return (
    <div
      className="lr-studio-onboarding"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lr-studio-onboarding-title"
      data-logos-studio-onboarding="1"
    >
      <div className="lr-studio-onboarding__backdrop" aria-hidden="true" />
      <div className="lr-studio-onboarding__panel">
        <p className="lr-studio-onboarding__eyebrow">연구 프로필 · 2문항</p>
        <h2 id="lr-studio-onboarding-title" className="lr-studio-onboarding__title">
          {step === 1 ? "오늘 연구 맥락을 선택하세요" : "핵심 주제 영역을 선택하세요"}
        </h2>
        <p className="lr-studio-onboarding__lead">
          {step === 1
            ? "학술 경로 검증과 묵상·고민 모드는 프리셋·ECS 표시가 다릅니다."
            : "선택에 맞는 프리셋·슬라이스가 자동으로 연결됩니다."}
        </p>

        {step === 1 ? (
          <div className="lr-studio-onboarding__choices" role="group" aria-label="연구 맥락">
            <button
              type="button"
              className={`lr-studio-onboarding__choice${audienceMode === "academic" ? " lr-studio-onboarding__choice--active" : ""}`}
              onClick={() => setAudienceMode("academic")}
            >
              <strong>학술 연구</strong>
              <span>GraphRAG 경로 · citation lock · ECS</span>
            </button>
            <button
              type="button"
              className={`lr-studio-onboarding__choice${audienceMode === "pastoral" ? " lr-studio-onboarding__choice--active" : ""}`}
              onClick={() => setAudienceMode("pastoral")}
            >
              <strong>묵상·고민</strong>
              <span>구절·경로 관측 · 상담·치료 아님</span>
            </button>
          </div>
        ) : (
          <div className="lr-studio-onboarding__choices" role="group" aria-label="주제 영역">
            {LOGOS_STUDIO_ONBOARDING_TOPICS.map((topic) => (
              <button
                key={topic.id}
                type="button"
                className={`lr-studio-onboarding__choice${topicId === topic.id ? " lr-studio-onboarding__choice--active" : ""}`}
                onClick={() => setTopicId(topic.id)}
              >
                <strong>{topic.label_ko}</strong>
                {topic.slot_label_ko ? <span>{topic.slot_label_ko}</span> : null}
              </button>
            ))}
          </div>
        )}

        <div className="lr-studio-onboarding__actions">
          {step === 2 ? (
            <button type="button" className="lr-btn lr-btn-ghost" onClick={() => setStep(1)}>
              이전
            </button>
          ) : (
            <button type="button" className="lr-btn lr-btn-ghost" onClick={onSkip}>
              건너뛰기
            </button>
          )}
          {step === 1 ? (
            <button type="button" className="lr-btn lr-btn-primary" onClick={() => setStep(2)}>
              다음
            </button>
          ) : (
            <button
              type="button"
              className="lr-btn lr-btn-primary"
              onClick={() => selectedTopic && finish(selectedTopic)}
            >
              연구 시작
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
