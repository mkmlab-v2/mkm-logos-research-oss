"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { IntentChipRowV2 } from "@/components/shell/IntentChipRowV2";
import { UniverseHubDisclaimerCollapsible } from "@/components/shell/UniverseHubDisclaimerCollapsible";
import {
  HUB_DISCOVER_COPY,
  type HubDiscoverLocale,
} from "@/lib/universeHubDiscoverCopyV2";
import { resolveHubAskRoute, type HubIntentId } from "@/lib/universeHubIntentRouterV2";

export function UniverseCenterAskV2() {
  const [locale, setLocale] = useState<HubDiscoverLocale>("ko");
  const [question, setQuestion] = useState("");
  const [intent, setIntent] = useState<HubIntentId | null>(null);
  const copy = HUB_DISCOVER_COPY[locale];

  const [submitError, setSubmitError] = useState<string | null>(null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const route = resolveHubAskRoute(question, intent);
    if (!route) {
      setSubmitError(copy.validationMissing);
      return;
    }
    setSubmitError(null);
    window.location.href = route;
  }

  function toggleLocale() {
    setLocale((prev) => (prev === "ko" ? "en" : "ko"));
  }

  return (
    <section className="universe-hub-ask" aria-labelledby="universe-hub-ask-title">
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
      <p className="universe-hub-ask-lead">{copy.lead}</p>

      <p className="universe-hub-ask-b2b">
        {copy.b2bPrefix}{" "}
        <Link href="/hub/customize" className="universe-hub-ask-b2b-link">
          {copy.b2bLink}
        </Link>
      </p>

      <IntentChipRowV2 selected={intent} onSelect={setIntent} />

      <form className="universe-hub-ask-form" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="universe-hub-question">
          질문
        </label>
        <input
          id="universe-hub-question"
          className="universe-hub-ask-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={copy.placeholder}
          maxLength={500}
          autoComplete="off"
        />
        <button type="submit" className="universe-hub-ask-submit">
          {copy.submit}
        </button>
      </form>

      {submitError ? (
        <p className="universe-hub-ask-error" role="alert">
          {submitError}
        </p>
      ) : null}

      <p className="universe-hub-ask-routing-note">{copy.routingNote}</p>

      <UniverseHubDisclaimerCollapsible defaultOpen={false} />
    </section>
  );
}
