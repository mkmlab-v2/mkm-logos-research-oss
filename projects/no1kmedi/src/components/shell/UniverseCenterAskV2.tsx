"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { HubAskSubmitIcon } from "@/components/shell/HubAskSubmitIcon";
import { useHubDiscoverLayout } from "@/components/shell/HubDiscoverLayoutContext";
import { IntentChipRowV2 } from "@/components/shell/IntentChipRowV2";
import { UniverseHubDisclaimerCollapsible } from "@/components/shell/UniverseHubDisclaimerCollapsible";
import {
  HUB_DISCOVER_COPY,
  type HubDiscoverLocale,
} from "@/lib/universeHubDiscoverCopyV2";
import { resolveHubAskRoute, type HubIntentId } from "@/lib/universeHubIntentRouterV2";

export function UniverseCenterAskV2() {
  const { discoverMinimal } = useHubDiscoverLayout();
  const [locale, setLocale] = useState<HubDiscoverLocale>("ko");
  const [question, setQuestion] = useState("");
  const [intent, setIntent] = useState<HubIntentId | null>(null);
  const copy = HUB_DISCOVER_COPY[locale];

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    const route = resolveHubAskRoute(question, intent);
    if (!route) {
      setSubmitError(copy.validationMissing);
      return;
    }
    setSubmitError(null);
    setIsSubmitting(true);
    window.location.href = route;
  }

  function toggleLocale() {
    setLocale((prev) => (prev === "ko" ? "en" : "ko"));
  }

  const sectionClass = discoverMinimal
    ? "universe-hub-ask universe-hub-ask--minimal"
    : "universe-hub-ask universe-hub-ask--v3";

  return (
    <section className={sectionClass} aria-labelledby="universe-hub-ask-title">
      {discoverMinimal ? (
        <div className="universe-hub-ask-minimal-brand">
          <h1 id="universe-hub-ask-title" className="universe-hub-ask-minimal-logo">
            JEMA AI
          </h1>
          <button
            type="button"
            className="universe-hub-locale-toggle universe-hub-locale-toggle--minimal"
            onClick={toggleLocale}
            aria-label={locale === "ko" ? "Switch to English" : "한국어로 전환"}
          >
            {copy.localeToggle}
          </button>
        </div>
      ) : (
        <div className="universe-hub-ask-title-row">
          <h1 id="universe-hub-ask-title" className="universe-hub-ask-title">
            {copy.title}
          </h1>
          <button
            type="button"
            className="universe-hub-locale-toggle"
            onClick={toggleLocale}
            aria-label={locale === "ko" ? "Switch to English" : "한국어로 전환"}
          >
            {copy.localeToggle}
          </button>
        </div>
      )}

      {!discoverMinimal ? <p className="universe-hub-ask-lead">{copy.lead}</p> : null}

      {!discoverMinimal ? (
        <p className="universe-hub-ask-b2b">
          {copy.b2bPrefix}{" "}
          <Link href="/hub/customize" className="universe-hub-ask-b2b-link">
            {copy.b2bLink}
          </Link>
        </p>
      ) : null}

      {!discoverMinimal ? <IntentChipRowV2 selected={intent} onSelect={setIntent} /> : null}

      <form
        className={`universe-hub-ask-form universe-hub-ask-form--pill${discoverMinimal ? " universe-hub-ask-form--minimal" : ""}`}
        onSubmit={onSubmit}
      >
        <label className="sr-only" htmlFor="universe-hub-question">
          질문
        </label>
        <div
          className={`universe-hub-ask-pill${discoverMinimal ? " universe-hub-ask-pill--minimal" : ""}${isSubmitting ? " is-submitting" : ""}`}
        >
          <input
            id="universe-hub-question"
            className="universe-hub-ask-input universe-hub-ask-input--pill"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={copy.placeholder}
            maxLength={500}
            autoComplete="off"
            disabled={isSubmitting}
            aria-invalid={submitError ? true : undefined}
            aria-describedby={submitError ? "universe-hub-ask-error" : undefined}
          />
          <button
            type="submit"
            className={`universe-hub-ask-submit universe-hub-ask-submit--pill${discoverMinimal ? " universe-hub-ask-submit--icon" : ""}`}
            aria-label={copy.submit}
            disabled={isSubmitting}
            aria-busy={isSubmitting}
          >
            {discoverMinimal ? <HubAskSubmitIcon /> : copy.submit}
          </button>
        </div>
      </form>

      {discoverMinimal ? <IntentChipRowV2 selected={intent} onSelect={setIntent} /> : null}

      {submitError ? (
        <p id="universe-hub-ask-error" className="universe-hub-ask-error" role="alert">
          {submitError}
        </p>
      ) : null}

      {discoverMinimal ? (
        <p className="universe-hub-ask-minimal-foot">{copy.routingNote}</p>
      ) : (
        <p className="universe-hub-ask-routing-note">{copy.routingNote}</p>
      )}

      <UniverseHubDisclaimerCollapsible defaultOpen={false} />
    </section>
  );
}
