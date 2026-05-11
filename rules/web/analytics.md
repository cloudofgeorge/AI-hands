# Analytics Integration Rule

## Purpose

Use this rule when adding or maintaining analytics in a Next.js App Router project that runs multiple analytics providers in parallel. The goal is to keep tracking reliable, privacy-aware, consent-gated, and easy to extend.

This rule covers:

- Plausible Analytics
- Google Tag Manager
- Yandex.Metrika
- Cookie consent gating
- A unified analytics service
- A React hook for product code
- Layout wiring
- Event naming and rollout checklist

## Table of Contents

1. [Core Principles](#core-principles)
2. [Recommended Architecture](#recommended-architecture)
3. [Cookie Consent Layer](#1-cookie-consent-layer)
4. [Plausible Analytics](#2-plausible-analytics)
5. [Google Tag Manager](#3-google-tag-manager)
6. [Yandex.Metrika](#4-yandexmetrika)
7. [Unified Analytics Class](#5-unified-analytics-class)
8. [React Hook: `useAnalytics`](#6-react-hook-useanalytics)
9. [Layout Wiring](#7-layout-wiring)
10. [Adding a New Event](#8-adding-a-new-event)
11. [Checklist for a New Project](#9-checklist-for-a-new-project)
12. [Agent Implementation Instructions](#agent-implementation-instructions)
13. [Do Not](#do-not)

## Core Principles

AI agents must follow these principles before writing analytics code:

- Do not load non-essential analytics scripts until the user has granted consent.
- Keep provider-specific code isolated from product UI.
- Expose one unified tracking API to the application.
- Make analytics failures non-blocking.
- Avoid tracking personally identifiable information unless the project explicitly requires it and has a legal basis.
- Use environment variables for provider IDs and runtime configuration.
- Keep event names stable, documented, and easy to search.
- Make server-rendered layouts safe by keeping browser-only analytics code inside client components.

## Recommended Architecture

Use this structure unless the project already has a strong convention:

```text
src/
  app/
    layout.tsx
  components/
    analytics/
      AnalyticsProvider.tsx
      ConsentBanner.tsx
  lib/
    analytics/
      analytics.ts
      consent.ts
      plausible.ts
      gtm.ts
      yandex.ts
      events.ts
```

The preferred flow is:

```text
User grants consent
  -> Consent state is stored
  -> AnalyticsProvider loads enabled scripts
  -> App calls useAnalytics()
  -> Unified analytics class routes events to each enabled provider
```

## 1. Cookie Consent Layer

Analytics must be controlled by an explicit consent layer.

Rules:

- Store consent in a durable client-side location such as a cookie or `localStorage`.
- Do not initialize Plausible, GTM, or Yandex.Metrika before analytics consent is granted.
- Provide a way to reject analytics.
- Provide a way to change consent later if the product has a settings area.
- Treat unknown consent as denied until the user chooses.
- Keep consent code independent from any single analytics provider.

Recommended consent model:

```ts
export type ConsentState = {
  analytics: boolean;
  updatedAt: string;
};
```

Use a small helper module for consent reads and writes:

```ts
export function hasAnalyticsConsent(): boolean {
  if (typeof window === "undefined") return false;

  const raw = window.localStorage.getItem("cookie-consent");
  if (!raw) return false;

  try {
    const consent = JSON.parse(raw) as ConsentState;
    return consent.analytics === true;
  } catch {
    return false;
  }
}
```

## 2. Plausible Analytics

Use Plausible for lightweight privacy-friendly pageviews and custom events.

Rules:

- Load the Plausible script only after analytics consent.
- Read the domain and optional script URL from environment variables.
- Use custom events for meaningful product actions, not every click.
- Keep Plausible calls wrapped in a provider adapter.
- Guard all browser globals with `typeof window !== "undefined"`.

Recommended environment variables:

```text
NEXT_PUBLIC_PLAUSIBLE_DOMAIN=example.com
NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL=https://plausible.io/js/script.js
```

Adapter shape:

```ts
declare global {
  interface Window {
    plausible?: (
      eventName: string,
      options?: {
        props?: Record<string, string | number | boolean>;
      },
    ) => void;
  }
}

export function trackPlausibleEvent(
  name: string,
  props?: Record<string, string | number | boolean>,
) {
  if (typeof window === "undefined") return;
  if (!window.plausible) return;

  window.plausible(name, { props });
}
```

## 3. Google Tag Manager

Use Google Tag Manager when the project needs flexible marketing tags, ad pixels, or third-party integrations managed outside the codebase.

Rules:

- Load the GTM script only after analytics consent.
- Use `dataLayer.push()` through a wrapper function.
- Do not scatter raw `dataLayer` calls across UI components.
- Include event names and payloads that are compatible with downstream GTM tags.
- Never send secrets, access tokens, raw emails, phone numbers, or full names.

Recommended environment variable:

```text
NEXT_PUBLIC_GTM_ID=GTM-XXXXXXX
```

Adapter shape:

```ts
declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
  }
}

export function trackGtmEvent(
  event: string,
  payload: Record<string, unknown> = {},
) {
  if (typeof window === "undefined") return;

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    event,
    ...payload,
  });
}
```

## 4. Yandex.Metrika

Use Yandex.Metrika when the project needs analytics coverage for audiences or markets where it is required.

Rules:

- Load Yandex.Metrika only after analytics consent.
- Read the counter ID from an environment variable.
- Keep all `ym()` calls inside a Yandex adapter.
- Guard against missing or blocked scripts.
- Track goals through named wrapper functions or the unified analytics service.

Recommended environment variable:

```text
NEXT_PUBLIC_YANDEX_METRIKA_ID=00000000
```

Adapter shape:

```ts
declare global {
  interface Window {
    ym?: (...args: unknown[]) => void;
  }
}

export function trackYandexGoal(
  goal: string,
  params?: Record<string, unknown>,
) {
  if (typeof window === "undefined") return;
  if (!window.ym) return;

  const counterId = process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID;
  if (!counterId) return;

  window.ym(Number(counterId), "reachGoal", goal, params);
}
```

## 5. Unified Analytics Class

Create one application-facing analytics API. Product code should not know which providers are active.

Rules:

- Centralize all event routing in one class or module.
- Normalize event names before sending them to providers.
- Allow providers to fail independently.
- Keep provider payloads intentionally small.
- Make `track()` safe to call before scripts are fully loaded.

Recommended shape:

```ts
export type AnalyticsEventPayload = Record<
  string,
  string | number | boolean
>;

export class Analytics {
  track(name: string, payload: AnalyticsEventPayload = {}) {
    if (!hasAnalyticsConsent()) return;

    trackPlausibleEvent(name, payload);
    trackGtmEvent(name, payload);
    trackYandexGoal(name, payload);
  }

  pageView(path: string) {
    this.track("page_view", { path });
  }
}

export const analytics = new Analytics();
```

## 6. React Hook: `useAnalytics`

Expose analytics to React components through a hook.

Rules:

- Keep components free of provider-specific imports.
- Memoize callbacks when useful.
- Return stable methods such as `track`, `pageView`, and domain-specific helpers.
- Do not call analytics during server rendering.

Recommended shape:

```ts
"use client";

import { useCallback } from "react";
import { analytics, type AnalyticsEventPayload } from "@/lib/analytics/analytics";

export function useAnalytics() {
  const track = useCallback(
    (name: string, payload?: AnalyticsEventPayload) => {
      analytics.track(name, payload);
    },
    [],
  );

  return { track };
}
```

Example usage:

```tsx
"use client";

import { useAnalytics } from "@/lib/analytics/useAnalytics";

export function CheckoutButton() {
  const { track } = useAnalytics();

  return (
    <button
      type="button"
      onClick={() => track("checkout_started", { source: "pricing_page" })}
    >
      Start checkout
    </button>
  );
}
```

## 7. Layout Wiring

Wire analytics once near the application root.

Rules:

- Keep `app/layout.tsx` as a server component unless the project already uses a client layout.
- Mount a client-side `AnalyticsProvider` inside the layout body.
- Use Next.js `Script` with an appropriate loading strategy for third-party scripts.
- Re-check consent before rendering scripts.
- Keep consent UI separate from script loading when possible.

Recommended layout pattern:

```tsx
// src/app/layout.tsx
import { AnalyticsProvider } from "@/components/analytics/AnalyticsProvider";
import { ConsentBanner } from "@/components/analytics/ConsentBanner";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AnalyticsProvider />
        {children}
        <ConsentBanner />
      </body>
    </html>
  );
}
```

Provider responsibilities:

- Read consent on mount.
- Load scripts only when consent is true.
- Listen for consent changes if the banner can update consent without a full page reload.
- Avoid rendering duplicate scripts.

## 8. Adding a New Event

When adding an analytics event, agents must update the event catalog first.

Recommended event catalog:

```ts
export const ANALYTICS_EVENTS = {
  PAGE_VIEW: "page_view",
  SIGN_UP_STARTED: "sign_up_started",
  SIGN_UP_COMPLETED: "sign_up_completed",
  CHECKOUT_STARTED: "checkout_started",
  CHECKOUT_COMPLETED: "checkout_completed",
  CONTACT_FORM_SUBMITTED: "contact_form_submitted",
} as const;
```

Event naming rules:

- Use `snake_case`.
- Prefer past-tense action names for completed actions, such as `sign_up_completed`.
- Use present/progress names for started flows, such as `checkout_started`.
- Keep names stable after release.
- Do not encode dynamic values into event names.
- Put dynamic values in the payload.

Payload rules:

- Use small flat objects.
- Prefer IDs, categories, plans, sources, and booleans.
- Do not send raw user-generated text.
- Do not send sensitive personal data.
- Do not send payment details.

Good:

```ts
track(ANALYTICS_EVENTS.CHECKOUT_STARTED, {
  plan: "pro",
  billing_period: "annual",
  source: "pricing_page",
});
```

Avoid:

```ts
track(`checkout_started_for_${email}`, {
  card_number,
  message,
});
```

## 9. Checklist for a New Project

Before marking analytics integration complete, verify:

- Consent banner exists and supports accept and reject actions.
- Unknown consent does not load analytics scripts.
- Accepted consent loads Plausible, GTM, and Yandex.Metrika when configured.
- Rejected consent keeps analytics scripts unloaded.
- Provider IDs are read from `NEXT_PUBLIC_*` environment variables.
- Missing provider IDs fail silently and do not break the app.
- Product components use `useAnalytics()` or the unified analytics service.
- No UI component imports Plausible, GTM, or Yandex adapters directly.
- Event names are stored in a central catalog.
- Events do not include sensitive personal data.
- Page views are tracked once per navigation.
- Analytics code is safe in server-rendered App Router routes.
- TypeScript passes.
- Linting passes.
- Manual browser testing confirms scripts appear only after consent.

## Agent Implementation Instructions

When an AI agent applies this rule:

1. Inspect the existing project structure before creating files.
2. Reuse the project's current consent, environment, script-loading, and naming patterns when they exist.
3. If no analytics architecture exists, create the modules described in this rule.
4. Keep the first implementation minimal and complete: consent, provider loading, unified tracking, hook, and layout wiring.
5. Add or update tests when the project already has test coverage for hooks, utilities, or layout behavior.
6. Run the project's available validation commands, usually `npm run lint`, `npm run typecheck`, and relevant tests.
7. Document any required environment variables in the project's `.env.example` or setup documentation.

## Do Not

- Do not load analytics in `head` unconditionally.
- Do not place provider scripts directly in random pages.
- Do not call `window`, `document`, `dataLayer`, `plausible`, or `ym` from server components.
- Do not block rendering if an analytics script fails.
- Do not duplicate the same event call in both a component and a provider callback.
- Do not track form contents, passwords, payment details, access tokens, or private messages.
- Do not add analytics packages if a small script adapter is enough for the existing project.
